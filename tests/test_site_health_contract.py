"""What `site_health.yml` must actually verify before it says a friend can look.

This workflow is the go/no-go for a real test — `docs/V1.md`, `TODOS.md` and bar
row H7 all cite its output as evidence — so what it MEASURES has to be what the
evidence CLAIMS. Two PR #80 findings, same seat: it read `/api/health` and printed
*"a friend with this link can open it"* (`CLASS:missing-product-surface-verification`
— a healthy diagnostic endpoint says nothing about a blank or auth-walled feed
page), and it proved the bypass HEADER while the docs hand friends a
QUERY-PARAMETER link (`CLASS:missing-friend-bypass-path-check`).

THE LIMIT, stated: these are text assertions on the workflow, not executions of
it. They prove the checks exist, target the right URLs and fail closed — not that
curl behaves. That is proven by the workflow's own runs, quoted in `docs/V1.md`.
"""
from __future__ import annotations

import pathlib
import re
import subprocess

import pytest
import yaml

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_WORKFLOW = _ROOT / ".github" / "workflows" / "site_health.yml"


@pytest.fixture(scope="module")
def text() -> str:
    return _WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def script(text: str) -> str:
    """The main step's shell body, so assertions cannot be satisfied by a comment."""
    doc = yaml.safe_load(text)
    steps = doc["jobs"]["check"]["steps"]
    body = next(s["run"] for s in steps if "run" in s and "/api/health" in s["run"])
    return "\n".join(line for line in body.splitlines()
                     if not line.lstrip().startswith("#"))


def test_it_fetches_the_product_surface_not_only_the_diagnostic(script: str):
    assert "/api/health" in script, "the diagnostic read must still happen"
    assert 'curl -sSL' in script, \
        "the product fetch must FOLLOW redirects — / redirects to /tonight"
    assert "feed_http_status" in script, \
        "the feed page's own status has to be reported as its own number"


def test_a_non_200_feed_page_fails_the_check(script: str):
    """A healthy diagnostic over a broken page must not be a green go/no-go."""
    assert 'if [ "$FEED_CODE" != "200" ]; then' in script
    segment = script[script.index('if [ "$FEED_CODE" != "200" ]'):]
    assert "exit 1" in segment[:600], "a broken feed page must fail, not warn"


def test_a_200_that_renders_nothing_also_fails(script: str):
    """The specific failure this check exists for: a 200 empty shell. Asserted
    against the page's own masthead, which every branch of
    web/app/(public)/tonight/page.tsx renders — including the empty-feed and error
    branches — so this proves "the page rendered", not "the page had data"."""
    assert 'grep -q "ONE LIVE" /tmp/feed.html' in script
    masthead = (_ROOT / "web" / "app" / "(public)" / "tonight" / "page.tsx").read_text(
        encoding="utf-8")
    assert "ONE LIVE" in masthead, (
        "the string this check greps for is no longer in the page — the check is "
        "now vacuous and would fail every run, or worse, be relaxed to compensate")


def test_it_verifies_the_QUERY_PARAM_link_form_friends_are_given(script: str):
    """Header success is not evidence about the link. The link is what gets sent."""
    assert "x-vercel-protection-bypass=" in script, \
        "the query-parameter form must be exercised, not just the header"
    assert "x-vercel-set-bypass-cookie=true" in script, \
        "the cookie parameter is what makes normal browsing work after the first " \
        "click — omitting it verifies a link that is not the one in the docs"
    assert "friend_link_http_status" in script


def test_the_friend_link_check_is_skipped_LOUDLY_when_there_is_no_secret(script: str):
    """Absent must never look like verified — the founding anti-pattern."""
    assert "friend_link: NOT CHECKED" in script


def test_the_link_form_checked_is_the_one_the_docs_hand_out():
    """A check that verifies a DIFFERENT URL shape than the docs publish is worse
    than none: it produces confidence about a string nobody uses."""
    script_text = _WORKFLOW.read_text(encoding="utf-8")
    for doc in ("docs/V1.md", "TODOS.md"):
        published = (_ROOT / doc).read_text(encoding="utf-8")
        if "x-vercel-protection-bypass" not in published:
            continue
        for param in ("x-vercel-protection-bypass=",
                      "x-vercel-set-bypass-cookie=true"):
            assert param in published and param in script_text, (
                f"{doc} publishes a bypass link but {param!r} is not in both the "
                f"doc and the workflow — the verified form and the published form "
                f"must be the same string")


def test_the_health_verdict_does_not_claim_the_friend_can_see_the_product(script: str):
    """The wording was the tell. `/api/health` returning 200 is evidence about
    `/api/health`; the friend claim belongs after the surface checks."""
    lines = script.splitlines()
    verdict_idx = next(i for i, ln in enumerate(lines)
                       if "VERDICT:" in ln and "PUBLIC" in ln)
    verdict_block = "\n".join(lines[verdict_idx:verdict_idx + 4])
    assert "a friend with this link can open it" not in verdict_block, (
        "this verdict fires on the /api/health status alone, so it must not make "
        "a claim about what a friend would see")
    assert "NOT evidence" in verdict_block, \
        "it should say what it is not evidence of, since it reads authoritative"


def test_the_gated_verdict_still_says_a_friend_cannot_see_it(script: str):
    """The negative claim IS supported by /api/health alone: if the host refuses
    the diagnostic, it refuses everything."""
    assert "A FRIEND CLICKING THIS LINK CANNOT SEE THE PRODUCT" in script


def test_event_count_zero_still_fails(script: str):
    """Unchanged property, asserted here so the additions above cannot have
    displaced it: a live site over an empty feed is a worse first impression than
    no site, so it fails rather than warns."""
    assert "event_count" in script
    assert "The site is up and the feed is EMPTY" in script


# ------------------------------------------------------------- secret custody
def test_BOTH_secret_bearing_trigger_paths_are_default_branch_only():
    """`CLASS:missing-secret-custody-regression-test` (openai/absence-only, PR #76 r2).

    This workflow reads `secrets.VERCEL_AUTOMATION_BYPASS`, and GitHub runs the file
    from the TRIGGERING REF — so a trigger reachable from an unreviewed branch hands
    the secret to YAML that branch controls. The guard existed but nothing bound it,
    so a future move of the `if:` or a widened trigger could reopen it silently.
    Secret custody is an invariant class; an invariant with no failing test is a
    convention.
    """
    doc = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    triggers = set(doc.get("on", doc.get(True)) or {})
    assert triggers == {"deployment_status", "workflow_dispatch"}, (
        f"the trigger set changed to {sorted(triggers)} — every new trigger needs "
        f"its own custody answer, so this test must be updated deliberately")

    condition = doc["jobs"]["check"].get("if", "")
    assert condition, "the job has no `if:` — the secret is unguarded"
    guard = re.compile(r"github\.ref_name\s*==\s*[^\n]*default_branch")
    # EVERY top-level alternative must carry the guard, or one path bypasses it.
    for branch in re.split(r"\|\|", condition):
        assert guard.search(branch), (
            f"this alternative runs WITHOUT a default-branch guard, so it can "
            f"execute branch-owned YAML with the secret: {branch.strip()!r}")
    assert "pull_request" not in triggers, \
        "a pull_request trigger is the exfiltration path this replaced"


def test_the_secret_is_only_ever_SENT_to_this_projects_own_hosts(script: str):
    """`CLASS:false-confidence-gate` (openai/attacker-smuggle, PR #76 r2), and the
    more important half of custody.

    The default-branch guard controls WHO may start the run. It does NOT control
    where the secret goes: the `url` input was arbitrary, so a dispatch from the
    default branch could post the bypass to any host on the internet — while the
    comments claimed the guard covered exactly that. The host is now allowlisted,
    and the check happens BEFORE the secret is read into a request.
    """
    assert "vercel.app" in script, "the allowlist must name this project's hosts"
    assert "refusing to send the Vercel bypass secret" in script, \
        "a foreign host must be refused with a reason, not silently allowed"
    # Ordering is the property: allowlist first, secret second.
    assert script.index("refusing to send the Vercel bypass secret") < \
        script.index("VERCEL_BYPASS:?"), \
        "the host allowlist must be evaluated BEFORE the secret is required"


@pytest.mark.parametrize("url,allowed", [
    ("https://onelive-git-x-sss-projects.vercel.app", True),
    ("https://onelive-git-x.vercel.app/api/health", True),
    ("https://onelive-git-x.vercel.app/", True),      # trailing slash normalised
    ("https://onelive-git-x.vercel.app///", True),
    ("https://onelive.com", True),
    ("https://www.onelive.com", True),
    ("https://evil.example", False),
    ("https://vercel.app.evil.example", False),
    ("http://x.vercel.app", False),          # not https
    ("ftp://x.vercel.app", False),
    ("https://attacker.io/vercel.app", False),
    # R-081, and the case that was ACTUALLY exploitable. bash's `*` matches `/`,
    # so an allowlist matched against the whole URL let a path supply the allowed
    # suffix. The row above passed only because `/vercel.app` lacks the leading
    # dot — it was refused for the wrong reason, which is why the hole survived a
    # test that looked like it covered this.
    ("https://attacker.io/x.vercel.app", False),
    ("https://attacker.io/x.vercel.app/", False),
    ("https://attacker.io/?q=x.vercel.app", False),
    # Userinfo: the real host is after the `@`.
    ("https://x.vercel.app@evil.example", False),
    ("https://evil.example@x.vercel.app", False),  # refused outright, not parsed
    ("https://", False),
    ("", False),
])
def test_the_host_allowlist_decides_correctly(url, allowed):
    """The arms are EXECUTED with bash, not pattern-matched as text: a broken arm
    placed after a catch-all would satisfy a grep and fail in production. This test
    is also why R-081 was found at all — the exploit is one bash run away, and no
    amount of reading the glob out loud produced it."""
    block = _allowlist_block()
    script_text = 'set -u\nBASE_URL="$1"\n' + block + '\necho ALLOWED\n'
    proc = subprocess.run(["bash", "-c", script_text, "bash", url],
                          capture_output=True, text=True, timeout=60)
    got = proc.returncode == 0 and "ALLOWED" in proc.stdout
    assert got is allowed, (
        f"{url} -> {'allowed' if got else 'refused'}, expected "
        f"{'allowed' if allowed else 'refused'}: {proc.stdout}{proc.stderr}")


def test_the_allowlist_matches_a_HOST_and_not_the_whole_url():
    """R-081 as a property, so the fix cannot be undone by a tidy-up.

    The regression was a single-token difference — `case "$BASE_URL"` where
    `case "$HOST"` was needed — and it is invisible on review because the arm
    pattern reads correctly either way. Binding the property means the extracted
    host must exist and the domain arms must be applied to it.
    """
    block = _allowlist_block()
    assert 'HOST="${BASE_URL#https://}"' in block, \
        "the scheme must be stripped to obtain a host"
    assert 'HOST="${HOST%%/*}"' in block, \
        "everything from the first / onward must be discarded — that path is " \
        "exactly what supplied the allowed suffix in R-081"
    assert 'case "$HOST" in' in block, "the domain arms must be applied to the host"
    assert ".vercel.app) ;;" in block
    assert 'https://*.vercel.app)' not in block, (
        "the domain arm is matching a full URL again — bash's `*` matches `/`, so "
        "this re-opens R-081: https://attacker.io/x.vercel.app is accepted")


def test_a_trailing_slash_cannot_produce_a_double_slash_request(script: str):
    """The originating nit. `$BASE_URL/api/health` with a trailing-slash input
    requests `...//api/health`, which some hosts 404 — a green workflow reporting a
    broken site, or a red one reporting a fine site."""
    assert 'while [ "${BASE_URL%/}" != "$BASE_URL" ]' in script, \
        "trailing slashes must be stripped, and repeatedly — '.../' and '...///' " \
        "are both things a founder can paste into a dispatch box"


def _allowlist_block() -> str:
    """The URL-normalisation and host-allowlist region, lifted verbatim.

    Delimited by sentinel comments rather than by "first `case` to first `esac`":
    the region is now three `case` blocks (scheme, userinfo, domain) and an index
    scan would silently lift only the first, leaving the real allowlist untested —
    the failure mode where a test keeps passing while covering nothing.
    """
    doc = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    body = next(s["run"] for s in doc["jobs"]["check"]["steps"]
                if "run" in s and "/api/health" in s["run"])
    lines = body.splitlines()
    start = next(i for i, ln in enumerate(lines)
                 if "host-allowlist:begin" in ln)
    end = next(i for i, ln in enumerate(lines[start:], start)
               if "host-allowlist:end" in ln)
    block = "\n".join(lines[start + 1:end])
    assert "case" in block and "exit 1" in block, (
        "the sentinel-delimited region no longer contains the allowlist — the "
        "markers moved and this extractor is now testing nothing")
    return block
