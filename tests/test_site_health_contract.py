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
