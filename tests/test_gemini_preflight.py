"""Second-seat preflight: every branch, as a committed test.

#72 r4 blocker (class: untested-gate-branch): the first version of this
preflight lived inline in the workflow YAML and was verified by local
simulation, which is not repo-verifiable and can regress silently until
the live review gate is already broken. The logic now lives in
tools/gemini_preflight.py with an injectable transport, so absent-key,
list-failure, pin-absent, quota-refused, and success are all real tests.

The transport doubles return recorded provider shapes; no network.
"""
import json
import urllib.error

import pytest

from tools import gemini_preflight as gp


def _page(names, methods="generateContent", token=None):
    page = {"models": [{"name": f"models/{n}",
                        "supportedGenerationMethods": [methods]} for n in names]}
    if token:
        page["nextPageToken"] = token
    return page


class _Transport:
    """Records calls; answers list URLs from pages, probes from `probe`."""

    def __init__(self, pages, probe=None):
        self._pages = list(pages)
        self._probe = probe
        self.calls = []

    def __call__(self, url, key, payload=None):
        self.calls.append((url, payload))
        if ":generateContent" in url:
            if isinstance(self._probe, Exception):
                raise self._probe
            return self._probe or {"candidates": []}
        return self._pages.pop(0)


def _http_error(code, body):
    return urllib.error.HTTPError(
        "https://x", code, "err", {}, __import__("io").BytesIO(body.encode()))


def test_absent_key_is_an_explicit_empty_seat_not_a_failure(capsys):
    # The ONE deliberate non-failure: a credential the founder has not
    # minted must not turn into a red gate.
    transport = _Transport([])
    rc = gp.main(["gemini-flash-latest"], env={}, transport=transport)
    assert rc == 0
    assert transport.calls == []  # nothing was contacted
    assert "EXPLICIT empty seat" in capsys.readouterr().out


def test_blank_key_is_treated_as_absent(capsys):
    rc = gp.main(["m"], env={"GEMINI_API_KEY": "   "}, transport=_Transport([]))
    assert rc == 0
    assert "Preflight n/a" in capsys.readouterr().out


def test_unreachable_listing_fails_closed(capsys):
    def boom(url, key, payload=None):
        raise OSError("network down")

    rc = gp.main(["m"], env={"GEMINI_API_KEY": "k"}, transport=boom)
    assert rc == 1
    assert "could not list models" in capsys.readouterr().err


def test_pin_absent_from_the_list_fails_closed_and_prints_the_options(capsys):
    transport = _Transport([_page(["alpha-model", "beta-model"])])
    rc = gp.main(["gemini-2.5-flash"], env={"GEMINI_API_KEY": "k"},
                 transport=transport)
    assert rc == 1
    out = capsys.readouterr()
    assert "alpha-model" in out.out and "beta-model" in out.out
    assert "not among the models advertised" in out.err
    assert "Do not guess" in out.err


def test_advertised_but_quota_refused_fails_closed(capsys):
    # THE r4 BLOCKER, pinned: listing shows EXISTENCE, and the original
    # failure was 429 `limit: 0` — a quota condition no list can reveal.
    # A model that lists fine but refuses the call must still be caught
    # HERE, not three minutes later inside the review.
    body = json.dumps({"error": {"code": 429, "message": "limit: 0"}})
    transport = _Transport([_page(["gemini-2.5-pro"])],
                           probe=_http_error(429, body))
    rc = gp.main(["gemini-2.5-pro"], env={"GEMINI_API_KEY": "k"},
                 transport=transport)
    assert rc == 1
    err = capsys.readouterr().err
    assert "advertised but NOT callable" in err
    assert "429" in err and "limit: 0" in err


def test_retired_model_reports_its_own_404_body(capsys):
    body = json.dumps({"error": {
        "code": 404, "message": "no longer available to new users"}})
    transport = _Transport([_page(["gemini-2.5-flash"])],
                           probe=_http_error(404, body))
    rc = gp.main(["gemini-2.5-flash"], env={"GEMINI_API_KEY": "k"},
                 transport=transport)
    assert rc == 1
    assert "no longer available to new users" in capsys.readouterr().err


def test_probe_transport_failure_fails_closed(capsys):
    transport = _Transport([_page(["m"])], probe=OSError("reset"))
    rc = gp.main(["m"], env={"GEMINI_API_KEY": "k"}, transport=transport)
    assert rc == 1
    assert "cannot prove callability" in capsys.readouterr().err


def test_callable_pin_passes_and_actually_probed(capsys):
    transport = _Transport([_page(["gemini-flash-latest", "other"])])
    rc = gp.main(["gemini-flash-latest"], env={"GEMINI_API_KEY": "k"},
                 transport=transport)
    assert rc == 0
    out = capsys.readouterr().out
    assert "answered a live generateContent probe" in out
    # The probe is not decorative: assert the call really happened, with a
    # bounded body, against the PINNED model.
    probe_calls = [c for c in transport.calls if ":generateContent" in c[0]]
    assert len(probe_calls) == 1
    url, payload = probe_calls[0]
    assert url.endswith("/models/gemini-flash-latest:generateContent")
    assert payload["generationConfig"]["maxOutputTokens"] == 1


def test_unexhausted_pagination_raises_and_fails_the_gate_closed(capsys):
    # #72 r5 BLOCKER: the cap is a runaway backstop, not a truncation
    # point. Hitting it with a token still outstanding must RAISE — a
    # partial registry can report a perfectly callable pin as absent,
    # which is the false-confidence shape this tool exists to remove.
    endless = _Transport([_page([f"m{i}"], token=f"t{i}") for i in range(gp._MAX_PAGES)])
    with pytest.raises(RuntimeError, match="INCOMPLETE"):
        gp.callable_models("k", endless)

    # ...and through main(), that surfaces as a fail-closed exit, never a
    # confident "pin absent" verdict computed from half a registry.
    endless2 = _Transport([_page([f"m{i}"], token=f"t{i}") for i in range(gp._MAX_PAGES)])
    rc = gp.main(["gemini-flash-latest"], env={"GEMINI_API_KEY": "k"},
                 transport=endless2)
    assert rc == 1
    assert "could not list models" in capsys.readouterr().err


def test_opaque_page_tokens_are_percent_encoded():
    # Provider tokens are opaque blobs; an unescaped reserved character
    # would corrupt the next request and silently truncate the walk.
    nasty = "a&b=c d/e?f#g"
    transport = _Transport([_page(["a"], token=nasty), _page(["b"])])
    assert gp.callable_models("k", transport) == ["a", "b"]
    second_url = transport.calls[1][0]
    assert nasty not in second_url  # never raw
    assert "pageToken=a%26b%3Dc%20d%2Fe%3Ff%23g" in second_url


def test_listing_is_paginated_to_exhaustion():
    # #72 r4 nit: pageSize is a page size, not a completeness guarantee —
    # a truncated list would report a good pin as absent.
    transport = _Transport([
        _page(["a"], token="tok1"),
        _page(["b"], token="tok2"),
        _page(["c"]),
    ])
    assert gp.callable_models("k", transport) == ["a", "b", "c"]
    assert "pageToken=tok1" in transport.calls[1][0]
    assert "pageToken=tok2" in transport.calls[2][0]


def test_models_without_generateContent_are_not_offered():
    transport = _Transport([_page(["embedder"], methods="embedContent")])
    assert gp.callable_models("k", transport) == []


def test_malformed_model_entries_do_not_crash_the_listing():
    # Gemini seat's r4 nit: extraction outside the try block turned a
    # surprising payload into a traceback instead of a diagnostic.
    transport = _Transport([{"models": [{}, {"name": "models/ok",
                                             "supportedGenerationMethods":
                                             ["generateContent"]}]}])
    assert gp.callable_models("k", transport) == ["ok"]


def test_bad_arguments_fail_loud(capsys):
    assert gp.main([], env={"GEMINI_API_KEY": "k"}, transport=_Transport([])) == 2
    assert gp.main(["  "], env={"GEMINI_API_KEY": "k"},
                   transport=_Transport([])) == 2
    assert "exactly one argument" in capsys.readouterr().err


# --- the WORKFLOW branch that decides whether this gate runs at all -----
# #72 r6 blocker (class: fail-open-on-custody-misconfig): the tool's own
# branches were tested, but not the YAML condition deciding whether the
# secret-holding preflight executes. That branch can permanently treat
# "tool absent on trusted base" as non-failure while every test stays
# green — so the custody-critical shape is asserted here.


def _preflight_step():
    import pathlib

    import yaml

    workflow = yaml.safe_load(
        (pathlib.Path(gp.__file__).parent.parent / ".github" / "workflows"
         / "adversarial-review.yml").read_text())
    steps = workflow["jobs"]["adversarial-review"]["steps"]
    matches = [s for s in steps if "Preflight" in (s.get("name") or "")]
    assert len(matches) == 1, "exactly one preflight step must exist"
    return matches[0]


def test_workflow_runs_the_preflight_from_the_TRUSTED_BASE_copy():
    # It holds GEMINI_API_KEY; PR-supplied code must never be the thing
    # that holds a secret.
    run = _preflight_step()["run"]
    assert 'git show "$TRUSTED_BASE:tools/gemini_preflight.py"' in run
    assert "python3 -I /tmp/trusted/gemini_preflight.py" in run
    assert "python3 -I tools/gemini_preflight.py" not in run


def test_workflow_separates_ABSENCE_from_FETCH_FAILURE():
    # #72 r7 blocker (found by the Gemini seat): `git show ... > file
    # 2>/dev/null` conflates "the tool is not on base" with "the write
    # failed", and routed BOTH to the bootstrap skip — so any redirection
    # problem would silently disable the callability proof forever.
    # Existence is now tested on its own, and the step owns its directory
    # instead of inheriting it from an earlier step's side effect.
    run = _preflight_step()["run"]
    assert "mkdir -p /tmp/trusted" in run, (
        "the step must create its own output directory, not depend on "
        "another step having done it")
    assert 'git cat-file -e "$TRUSTED_BASE:tools/gemini_preflight.py"' in run, (
        "existence must be tested separately from fetching, or a write "
        "failure reads as absence and falls into the bootstrap skip")
    # The fetch itself must NOT swallow errors: no 2>/dev/null on the
    # redirecting git show, so set -e aborts the step on any failure.
    fetch_line = next(l for l in run.splitlines()
                      if 'git show "$TRUSTED_BASE:tools/gemini_preflight.py"' in l)
    assert "2>/dev/null" not in fetch_line
    assert "set -euo pipefail" in run


def test_workflow_bootstrap_skip_is_BOUNDED_and_removal_fails_closed():
    # The skip must be reachable ONLY while the PR itself carries the tool
    # (the bootstrap PR introducing it), so it expires by construction at
    # merge. Absent on base AND absent from the PR means the mechanism was
    # removed after landing — a hard stop, never a skip.
    run = _preflight_step()["run"]
    assert 'elif [ -f tools/gemini_preflight.py ]; then' in run, (
        "the bootstrap skip must be conditioned on the PR carrying the tool, "
        "otherwise it never expires")
    tail = run.split("elif [ -f tools/gemini_preflight.py ]; then", 1)[1]
    assert "else" in tail and "exit 1" in tail, (
        "absent on base AND absent from the PR must fail closed, not skip")
    assert "::error::" in tail


def test_EVERY_trusted_base_tool_fetch_in_the_workflow_fails_closed():
    # #72 r6 HARDENING after the repeat-class alarm: fail-open-on-custody-
    # misconfig already had a structural fix (#65 r12, corrupt trust
    # ARTIFACT refuses everything) and recurred here as a missing trust
    # TOOL falling into a success path. The general form of the class:
    # ANY `git show "$TRUSTED_BASE:tools/..."` in this workflow is a
    # custody fetch, and a custody fetch that misses must never reach a
    # bare success path. This asserts that for every such fetch that
    # exists today and every one added later — which is what makes it a
    # class fix rather than a third instance patch.
    import pathlib
    import re

    import yaml

    text = (pathlib.Path(gp.__file__).parent.parent / ".github" / "workflows"
            / "adversarial-review.yml").read_text()
    workflow = yaml.safe_load(text)
    fetches = 0
    for step in workflow["jobs"]["adversarial-review"]["steps"]:
        run = step.get("run") or ""
        if not re.search(r'git show "\$TRUSTED_BASE:tools/', run):
            continue
        fetches += 1
        # Everything after the fetch must contain a terminating failure
        # path — `exit 1` — so an absent trusted tool cannot be shrugged off.
        assert "exit 1" in run, (
            f"step {step.get('name')!r} fetches a trusted-base tool but has no "
            "fail-closed path if it is absent (class: "
            "fail-open-on-custody-misconfig)")
        assert "::error::" in run, (
            f"step {step.get('name')!r} must say WHY it failed closed")
    assert fetches >= 2, (
        "expected at least the reviewer and preflight custody fetches — if "
        "this drops, the guard above is silently covering nothing")
