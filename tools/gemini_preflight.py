#!/usr/bin/env python3
"""Prove the second review seat's pinned model is CALLABLE by this key.

Greppable summary: the unusable-credential-tier class, mechanized (#72
r1/r3/r4). Two rounds were lost guessing model names from error strings —
`gemini-2.5-pro` answered 429 `limit: 0` (the free tier offers it at zero
quota) and `gemini-2.5-flash` answered 404 `no longer available to new
users` — each discovered only after a ~3-minute review had already run.

WHAT "CALLABLE" MEANS HERE, and why listing is not enough (#72 r4
blocker, class: false-confidence-gate): `models.list` reports which
models EXIST and advertise `generateContent`. It says nothing about this
key's quota, which is exactly the condition that produced the original
429. A mechanism that checks existence while claiming to prove
callability verifies a different property than the one it advertises. So
this tool does BOTH: it lists (to print the real options when the pin is
wrong) and then makes a MINIMAL generateContent call against the pinned
model. Only a completed call proves the tier can use it.

Fail-closed everywhere: an unreachable listing, a malformed payload, a
pin absent from the list, or a refused generateContent all exit non-zero
with a diagnostic. The ONE deliberate exception is an absent key — that
is the founder-minted-credential case the panel already handles with an
explicit empty seat, and turning "not yet minted" into red would be a
different defect wearing this fix's clothes.

The transport is injectable so every branch is a real test rather than a
local simulation (#72 r4 blocker, class: untested-gate-branch).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
# One token of output is enough to prove the call completes; this exists to
# exercise quota, not to get an answer.
PROBE_BODY = {
    "contents": [{"role": "user", "parts": [{"text": "ok"}]}],
    "generationConfig": {"maxOutputTokens": 1},
}


def _http_json(url: str, key: str, payload: dict | None = None) -> dict:
    """POST when payload is given, else GET. The key travels in a HEADER,
    never a query string, so it cannot ride into proxy logs or traces."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"x-goog-api-key": key}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Bounded page walk. 20 x 1000 is far beyond any real registry, so the cap
# is a runaway BACKSTOP, never a truncation point — reaching it with a token
# still outstanding raises (#72 r5, class: pagination-integrity-gap).
_MAX_PAGES = 20


def callable_models(key: str, transport=_http_json) -> list[str]:
    """Every model this key's account lists as supporting generateContent.

    PAGINATED TO EXHAUSTION, and that claim is enforced rather than
    asserted (#72 r5): `pageSize` is a page size, not a completeness
    guarantee. If the walk hits its cap while the provider still offers a
    nextPageToken, this RAISES and the caller fails closed, instead of
    returning a partial registry that could declare a perfectly callable
    pin absent — the same false-confidence shape this tool exists to
    remove.

    Page tokens are OPAQUE provider strings, so they are percent-encoded
    before entering the query: an unescaped reserved character would
    corrupt the next request and silently truncate the walk."""
    names: list[str] = []
    token = ""
    for _ in range(_MAX_PAGES):
        url = f"{BASE_URL}/models?pageSize=1000"
        if token:
            url += f"&pageToken={urllib.parse.quote(token, safe='')}"
        page = transport(url, key)
        for model in page.get("models") or []:
            methods = model.get("supportedGenerationMethods") or []
            name = model.get("name") or ""
            if "generateContent" in methods and name:
                names.append(name.removeprefix("models/"))
        token = page.get("nextPageToken") or ""
        if not token:
            return sorted(set(names))
    raise RuntimeError(
        f"model registry still offered a nextPageToken after {_MAX_PAGES} "
        "pages — the list is INCOMPLETE and must not be used as gate "
        "evidence (a partial registry can report a callable pin as absent)"
    )


def probe_generate(key: str, model: str, transport=_http_json) -> None:
    """Make the smallest real generateContent call. Raises on refusal —
    THIS is what proves quota, which listing never could."""
    transport(f"{BASE_URL}/models/{model}:generateContent", key, PROBE_BODY)


def main(argv: list[str] | None = None, *, env=None, transport=_http_json) -> int:
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    if len(argv) != 1 or not argv[0].strip():
        print("gemini_preflight: FAIL — expected exactly one argument, the "
              "pinned model id", file=sys.stderr)
        return 2
    pinned = argv[0].strip()
    key = (env.get("GEMINI_API_KEY") or "").strip()
    if not key:
        print("second seat: no GEMINI_API_KEY minted — the panel will print an "
              "EXPLICIT empty seat and run single-family. Preflight n/a.")
        return 0

    try:
        names = callable_models(key, transport)
    except Exception as exc:  # noqa: BLE001 — every failure mode is fail-closed
        print(f"::error::second seat: could not list models for this key "
              f"({type(exc).__name__}) — the pin cannot be proven callable, "
              "failing closed rather than discovering it mid-review",
              file=sys.stderr)
        return 1

    print(f"second seat: {len(names)} model(s) advertised to this key:")
    for name in names:
        print(f"  {name}")
    if pinned not in names:
        print(f"::error::second seat: pinned model {pinned!r} is not among the "
              "models advertised to this key (see the list above). Pin one of "
              "those names in the job-level GEMINI_REVIEW_MODEL and in "
              "tools/adversarial_review.py's GEMINI_DEFAULT_MODEL — the test "
              "that binds them keeps the pair in sync. Do not guess from an "
              "error message.", file=sys.stderr)
        return 1

    # Listing proved EXISTENCE. This proves this key may actually call it —
    # the quota condition behind the original 429, which no list can show.
    try:
        probe_generate(key, pinned, transport)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:600]
        print(f"::error::second seat: {pinned!r} is advertised but NOT callable "
              f"by this key — generateContent answered HTTP {exc.code}: {body} "
              "Listing shows what exists; only this call shows what your tier "
              "may use. Pin a model from the list above that this key can "
              "actually call.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"::error::second seat: probe call to {pinned!r} failed "
              f"({type(exc).__name__}) — cannot prove callability, failing "
              "closed", file=sys.stderr)
        return 1

    print(f"second seat: PINNED MODEL {pinned!r} is advertised AND answered a "
          "live generateContent probe — preflight OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
