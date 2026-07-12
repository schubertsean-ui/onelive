"""Security-invariant tests for api/clerk_auth.py (stealth-gate layer 2).

These are NOT behind an opt-in marker: they guard auth invariants and must run
in the default gate on every commit. The RS256 signature path runs for REAL — a
throwaway RSA keypair signs the test tokens and only the JWKS *lookup*
(`_signing_key_for_token`) is patched to return the matching public key. A token
signed by a different key therefore genuinely fails signature verification, so
these tests can actually fail (no mock rubber-stamping; see tools/test_audit.py).
"""
import datetime as dt
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.clerk_auth as clerk_auth
from api.clerk_auth import (
    AuthError,
    require_allowlisted_user,
    verify_and_authorize,
    verify_clerk_jwt,
)

ALLOWED_AZP = "https://app.onelive.test"
ALLOWED_EMAIL = "ops@onelive.test"


def _pem(key) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _pub_pem(key) -> bytes:
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


@pytest.fixture(scope="module")
def keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def other_keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def _stealth_env(monkeypatch):
    monkeypatch.setenv("ONELIVE_ALLOWLIST", f"{ALLOWED_EMAIL},other@onelive.test")
    monkeypatch.setenv("ONELIVE_CLERK_AZP_ALLOWED", ALLOWED_AZP)
    monkeypatch.setenv("ONELIVE_CLERK_JWKS_URL", "https://clerk.onelive.test/.well-known/jwks.json")
    monkeypatch.delenv("ONELIVE_CLERK_ISSUER", raising=False)
    # Reset the module-level JWKS client cache between tests.
    clerk_auth._jwks_clients.clear()


def _make_token(keypair, *, email=ALLOWED_EMAIL, azp=ALLOWED_AZP,
                exp_delta=3600, nbf_delta=-10, include_azp=True, include_email=True,
                include_nbf=True):
    now = dt.datetime.now(tz=dt.timezone.utc)
    payload = {
        "sub": "user_abc123",
        "iat": now,
        "exp": now + dt.timedelta(seconds=exp_delta),
    }
    if include_nbf:
        payload["nbf"] = now + dt.timedelta(seconds=nbf_delta)
    if include_azp:
        payload["azp"] = azp
    if include_email:
        payload["email"] = email
    return jwt.encode(payload, _pem(keypair), algorithm="RS256")


def _patch_key(keypair):
    # Patch only the JWKS network lookup; real RS256 verification still runs.
    return patch.object(clerk_auth, "_signing_key_for_token", return_value=_pub_pem(keypair))


# --- happy path --------------------------------------------------------------
def test_valid_allowlisted_token_passes(keypair):
    token = _make_token(keypair)
    with _patch_key(keypair):
        user = verify_and_authorize(token)
    assert user["email"] == ALLOWED_EMAIL
    assert user["azp"] == ALLOWED_AZP
    assert user["user_id"] == "user_abc123"
    assert user["role"] == "admin"


# --- signature ---------------------------------------------------------------
def test_bad_signature_rejected(keypair, other_keypair):
    # Token signed by other_keypair, but JWKS returns `keypair`'s public key.
    token = _make_token(other_keypair)
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 401


# --- temporal claims ---------------------------------------------------------
def test_expired_token_rejected(keypair):
    token = _make_token(keypair, exp_delta=-30, nbf_delta=-60)
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_not_yet_valid_token_rejected(keypair):
    token = _make_token(keypair, nbf_delta=3600)
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 401


def test_token_missing_nbf_rejected(keypair):
    # §4.7: nbf is REQUIRED, not merely verified-if-present. A validly signed
    # token that omits nbf must be refused, not accepted with no lower bound.
    token = _make_token(keypair, include_nbf=False)
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 401
    assert "nbf" in exc.value.detail.lower()


# --- GAP 1: azp --------------------------------------------------------------
def test_azp_not_in_allowed_set_rejected(keypair):
    token = _make_token(keypair, azp="https://evil.example.com")
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 403
    assert "azp" in exc.value.detail.lower()


def test_azp_missing_rejected_per_policy(keypair):
    token = _make_token(keypair, include_azp=False)
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 403
    assert "azp" in exc.value.detail.lower()


def test_list_valued_azp_rejected_cleanly_not_500(keypair):
    # A hostile/malformed token with a JSON-array azp must produce a clean
    # AuthError(403), never an unhashable-type TypeError surfacing as a 500.
    token = _make_token(keypair, azp=["https://evil.example.com", ALLOWED_AZP])
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 403
    assert "azp" in exc.value.detail.lower()


def test_non_string_azp_rejected_cleanly(keypair):
    # A numeric azp is likewise a malformed authorized-party claim -> 403 deny.
    token = _make_token(keypair, azp=12345)
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 403


def test_whitespace_only_azp_rejected(keypair):
    token = _make_token(keypair, azp="   ")
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 403


def test_empty_azp_allowlist_denies_all(keypair, monkeypatch):
    monkeypatch.setenv("ONELIVE_CLERK_AZP_ALLOWED", "")
    token = _make_token(keypair)
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_clerk_jwt(token)
    assert exc.value.status_code == 403


# --- email allowlist (independent second invariant) --------------------------
def test_valid_signature_but_non_allowlisted_email_rejected(keypair):
    token = _make_token(keypair, email="stranger@nowhere.test")
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_and_authorize(token)
    assert exc.value.status_code == 403
    assert "allowlist" in exc.value.detail.lower()


def test_empty_email_allowlist_denies_all(keypair, monkeypatch):
    monkeypatch.setenv("ONELIVE_ALLOWLIST", "")
    token = _make_token(keypair)
    with _patch_key(keypair):
        with pytest.raises(AuthError) as exc:
            verify_and_authorize(token)
    assert exc.value.status_code == 403


def test_case_insensitive_email_match(keypair):
    token = _make_token(keypair, email="OPS@OneLive.TEST")
    with _patch_key(keypair):
        user = verify_and_authorize(token)
    assert user["email"] == ALLOWED_EMAIL


def test_email_claim_whitespace_is_stripped(keypair):
    # Stray surrounding whitespace in the email claim must normalize to a match
    # (aligns with the web layer) rather than cause a false deny.
    token = _make_token(keypair, email="  ops@onelive.test  ")
    with _patch_key(keypair):
        user = verify_and_authorize(token)
    assert user["email"] == ALLOWED_EMAIL


# --- header parsing / dependency ---------------------------------------------
def test_missing_authorization_header_rejected():
    with pytest.raises(AuthError) as exc:
        require_allowlisted_user(authorization=None)
    assert exc.value.status_code == 401


def test_malformed_authorization_header_rejected():
    with pytest.raises(AuthError):
        require_allowlisted_user(authorization="Token abc.def.ghi")


def test_dependency_accepts_valid_bearer(keypair):
    token = _make_token(keypair)
    with _patch_key(keypair):
        user = require_allowlisted_user(authorization=f"Bearer {token}")
    assert user["email"] == ALLOWED_EMAIL


# --- router-level enforcement is real, not dead code -------------------------
def test_public_router_denies_unauthenticated_request():
    # Proves api.public's router-level dependency actually fires: no token =>
    # 401 BEFORE any DB access (so this needs no database).
    from api.public import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.get("/tonight")
    assert resp.status_code == 401
