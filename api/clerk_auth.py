"""Independent server-side Clerk session-JWT verification (stealth-launch layer 2).

The Next.js middleware (web/middleware.ts) is layer 1. This module is layer 2:
the API NEVER trusts the frontend alone. Every protected endpoint independently
verifies the Clerk session JWT here — signature (RS256 against Clerk's JWKS),
`exp`/`nbf`, the authorized-party (`azp`) claim, and the server-side email
allowlist — so a forged, replayed, or cross-origin token is refused even if the
frontend gate were bypassed.

GAP 1 — authorized-parties (`azp`) validation
----------------------------------------------
Clerk session tokens carry an `azp` claim naming the origin the token was minted
for. Skipping it (e.g. decoding with `verify_aud=False` and no further check) is
the CSRF / token-reuse hole that both Clerk and OWASP warn about: a token minted
for another origin would otherwise be accepted. We therefore validate `azp`
against an explicit allowlist (`ONELIVE_CLERK_AZP_ALLOWED`). References:
  - https://clerk.com/docs/guides/sessions/manual-jwt-verification
  - https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/10-Testing_JSON_Web_Tokens

Fail-closed policy (mirrors the web allowlist: empty config denies all)
-----------------------------------------------------------------------
  * `ONELIVE_CLERK_AZP_ALLOWED` unset/empty  -> deny ALL. We never run the
    stealth API without an explicit authorized-parties allowlist.
  * token carries `azp` in the allowlist     -> accepted.
  * token carries `azp` NOT in the allowlist -> rejected (the GAP-1 core case).
  * token carries NO `azp`                   -> rejected when an allowlist is
    configured: every legitimate Clerk browser-session token in our deployment
    carries `azp`, so a missing one means it did not originate from our
    configured front-end.
  * `ONELIVE_ALLOWLIST` unset/empty          -> deny ALL (email allowlist).
  * validly-signed token whose email is not on `ONELIVE_ALLOWLIST` -> rejected,
    independently of layer 1.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import jwt
from fastapi import Depends, Header, HTTPException

# --- config (read at request time so ops can rotate without a redeploy) ------


def _split_env_csv(name: str) -> List[str]:
    raw = os.getenv(name, "") or ""
    return [part.strip() for part in raw.split(",") if part.strip()]


def load_email_allowlist() -> set[str]:
    """Lowercased set of allowed emails from ONELIVE_ALLOWLIST. Empty => deny all."""
    return {e.lower() for e in _split_env_csv("ONELIVE_ALLOWLIST")}


def load_azp_allowed() -> set[str]:
    """Set of allowed authorized-party origins from ONELIVE_CLERK_AZP_ALLOWED."""
    return set(_split_env_csv("ONELIVE_CLERK_AZP_ALLOWED"))


def _jwks_url() -> str:
    url = os.getenv("ONELIVE_CLERK_JWKS_URL")
    if not url:
        # A misconfiguration, not a transient fault: fail loud (OPERATING_RULES §3.1).
        raise HTTPException(
            status_code=500,
            detail="server auth misconfigured: ONELIVE_CLERK_JWKS_URL is not set",
        )
    return url


# A single cached JWKS client per JWKS URL (PyJWKClient caches keys internally
# and refreshes on unknown-kid). This is the one network path; tests patch
# `_signing_key_for_token` so the RS256 verification itself runs for real.
_jwks_clients: Dict[str, "jwt.PyJWKClient"] = {}


def _signing_key_for_token(token: str):
    url = _jwks_url()
    client = _jwks_clients.get(url)
    if client is None:
        client = jwt.PyJWKClient(url)
        _jwks_clients[url] = client
    return client.get_signing_key_from_jwt(token).key


class AuthError(HTTPException):
    """401 by default — an invalid/absent credential, not a server fault."""

    def __init__(self, detail: str, status_code: int = 401) -> None:
        super().__init__(status_code=status_code, detail=detail)


def verify_clerk_jwt(token: str) -> Dict[str, Any]:
    """Verify a Clerk session JWT and return its claims, or raise AuthError.

    Verifies RS256 signature (against the JWKS key for the token's kid),
    `exp`/`nbf`, optional issuer, and the `azp` allowlist (GAP 1). Does NOT
    enforce the email allowlist — that is the caller's separate check so both
    invariants are visible at the call site.
    """
    azp_allowed = load_azp_allowed()
    if not azp_allowed:
        # Fail-closed: no authorized-parties configured => trust nothing.
        raise AuthError(
            "authorized-parties allowlist is empty; refusing all tokens", status_code=403
        )

    try:
        signing_key = _signing_key_for_token(token)
    except jwt.PyJWKClientError as exc:
        raise AuthError(f"could not resolve a signing key for token: {exc}")
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"malformed token: {exc}")

    decode_kwargs: Dict[str, Any] = {
        "algorithms": ["RS256"],
        # Clerk session tokens use `azp`, not `aud`, for the origin binding; we
        # validate `azp` explicitly below rather than relying on audience.
        # Both `exp` and `nbf` are required (§4.7): a validly-signed token that
        # omits either temporal bound is refused, not accepted with an implicit
        # "no lower bound".
        "options": {"require": ["exp", "nbf"], "verify_aud": False},
    }
    issuer = os.getenv("ONELIVE_CLERK_ISSUER")
    if issuer:
        decode_kwargs["issuer"] = issuer

    try:
        claims = jwt.decode(token, key=signing_key, **decode_kwargs)
    except jwt.ExpiredSignatureError:
        raise AuthError("token expired")
    except jwt.ImmatureSignatureError:
        raise AuthError("token not yet valid (nbf)")
    except jwt.InvalidIssuerError:
        raise AuthError("token issuer not accepted")
    except jwt.InvalidSignatureError:
        raise AuthError("token signature invalid")
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"token invalid: {exc}")

    azp = claims.get("azp")
    if azp is None:
        raise AuthError("token missing azp (authorized party); refused", status_code=403)
    # Type-check BEFORE the membership test: a list/dict/number `azp` (a malformed
    # or hostile token) must produce a clean 403 deny, never an unhashable-type
    # TypeError that surfaces as a 500 and looks like a server fault.
    if not isinstance(azp, str) or not azp.strip():
        raise AuthError("token azp is not a valid non-empty string; refused", status_code=403)
    azp = azp.strip()
    if azp not in azp_allowed:
        raise AuthError(f"token azp '{azp}' is not an authorized party", status_code=403)

    return claims


def _email_from_claims(claims: Dict[str, Any]) -> Optional[str]:
    # Clerk session tokens can carry the primary email under a few keys
    # depending on the JWT template; check the common ones.
    for key in ("email", "email_address", "primary_email_address"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            # Strip + lowercase so a claim with stray surrounding whitespace
            # matches the allowlist, mirroring the web layer's normalization.
            return value.strip().lower()
    return None


def verify_and_authorize(token: str) -> Dict[str, Any]:
    """Verify the token (signature/exp/nbf/azp) AND enforce the email allowlist.

    Returns a user dict on success; raises AuthError (401/403) otherwise. This is
    the full stealth check both the ops and public read paths share.
    """
    claims = verify_clerk_jwt(token)

    allowlist = load_email_allowlist()
    if not allowlist:
        # Fail-closed: no allowlisted emails configured => nobody is allowed.
        raise AuthError("email allowlist is empty; access denied", status_code=403)

    email = _email_from_claims(claims)
    if email is None:
        raise AuthError("token carries no email claim; access denied", status_code=403)
    if email not in allowlist:
        raise AuthError(f"'{email}' is not on the stealth allowlist", status_code=403)

    return {
        "user_id": claims.get("sub"),
        "email": email,
        "role": "admin",  # stealth: every allowlisted user is an operator
        "azp": claims.get("azp"),
    }


def _bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise AuthError("missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise AuthError("Authorization header must be 'Bearer <token>'")
    return parts[1].strip()


def require_allowlisted_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """FastAPI dependency: require a valid, allowlisted Clerk token. Fail-closed."""
    token = _bearer_token(authorization)
    return verify_and_authorize(token)
