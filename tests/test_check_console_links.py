"""Tests for tools/check_console_links.py.

Founder directive 2026-07-26: *"Always give me specific and accurate and working
links."* This tool is the mechanical half — it notices when one goes wrong.

The design point these tests protect: the tool must NEVER report a link it could
not see as passing. A dashboard URL behind a login answers 403; a policy-denied
host answers nothing; a wrong path 404s. Collapsing those three into one green
row would be the false-confidence gate this repo keeps catching.

No network here: `probe` is stubbed. Reachability is exercised for real on a
GitHub runner by `.github/workflows/site_health.yml`.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import urllib.error

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_console_links", _REPO_ROOT / "tools" / "check_console_links.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


LINKS = _load()


# ---------------------------------------------------------------- extraction
def test_the_real_deploy_doc_yields_the_console_links():
    urls = LINKS.urls_in_section(LINKS.DEPLOY_DOC.read_text(encoding="utf-8"))
    assert len(urls) >= 8, urls
    assert all(u.startswith("https://") for u in urls)
    # The two that unblock the founder asks must be in the table.
    assert any("deployment-protection" in u for u in urls)
    assert any("secrets/actions/new" in u for u in urls)


def test_urls_are_deduplicated_and_ordered():
    text = (f"{LINKS.SECTION_HEADING}\n<https://a.example/x> <https://a.example/x> "
            f"<https://b.example/y>\n")
    assert LINKS.urls_in_section(text) == ["https://a.example/x",
                                          "https://b.example/y"]


def test_only_the_console_section_is_scanned():
    text = (f"{LINKS.SECTION_HEADING}\n<https://inside.example/>\n"
            f"## Another section\n<https://outside.example/>\n")
    assert LINKS.urls_in_section(text) == ["https://inside.example/"]


def test_a_renamed_section_raises_rather_than_silently_finding_nothing():
    with pytest.raises(LookupError):
        LINKS.urls_in_section("# DEPLOY\n\n## Something else\n<https://x.example/>\n")


# --------------------------------------------------------------------- probe
def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x.example/", code, "msg", {}, None)


@pytest.mark.parametrize("code", [301, 302, 307, 401, 403])
def test_login_required_is_AUTH_not_broken(monkeypatch, code):
    # Expected for every dashboard link in the table.
    monkeypatch.setattr(LINKS.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(_http_error(code)))
    assert LINKS.probe("https://x.example/")[0] == "AUTH"


def test_404_is_BROKEN(monkeypatch):
    monkeypatch.setattr(LINKS.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(_http_error(404)))
    status, detail = LINKS.probe("https://x.example/")
    assert status == "BROKEN" and "404" in detail


def test_a_404_on_the_private_repo_is_PRIVATE_not_BROKEN(monkeypatch):
    """The false positive the first real CI run produced.

    This repo is private, so an anonymous request to any of its pages 404s
    whether the path is right or wrong. Calling that BROKEN made the gate fail on
    four correct links — a false-positive gate, which is worse than no gate
    because it teaches people to ignore red.
    """
    monkeypatch.setattr(LINKS.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(_http_error(404)))
    status, detail = LINKS.probe(
        "https://github.com/schubertsean-ui/onelive/settings/secrets/actions")
    assert status == "PRIVATE"
    assert "not visible" in detail
    # And a 404 elsewhere is still a real finding — the narrowing is targeted.
    assert LINKS.probe("https://github.com/other/repo/x")[0] == "BROKEN"


def test_a_workflow_link_is_verified_against_the_file_offline():
    """A private page cannot be probed, but the workflow file is right here."""
    status, detail = LINKS.probe(
        "https://github.com/schubertsean-ui/onelive/actions/workflows/site_health.yml")
    assert status == "PASS" and "exists" in detail


def test_a_workflow_link_pointing_at_nothing_is_BROKEN():
    status, detail = LINKS.probe(
        "https://github.com/schubertsean-ui/onelive/actions/workflows/no_such.yml")
    assert status == "BROKEN" and "does not exist" in detail


def test_the_offline_workflow_check_does_not_hit_the_network(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("probe made a network call for a workflow link")
    monkeypatch.setattr(LINKS.urllib.request, "urlopen", explode)
    assert LINKS.probe(
        "https://github.com/schubertsean-ui/onelive/actions/workflows/"
        "import_licensed.yml")[0] == "PASS"


def test_head_not_allowed_is_not_a_broken_link(monkeypatch):
    monkeypatch.setattr(LINKS.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(_http_error(405)))
    assert LINKS.probe("https://x.example/")[0] == "AUTH"


def test_a_policy_denial_is_BLOCKED_and_distinct_from_a_dead_host(monkeypatch):
    denied = urllib.error.URLError("Tunnel connection failed: 403 Forbidden")
    monkeypatch.setattr(LINKS.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(denied))
    assert LINKS.probe("https://x.example/")[0] == "BLOCKED"

    dead = urllib.error.URLError("[Errno -2] Name or service not known")
    monkeypatch.setattr(LINKS.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(dead))
    assert LINKS.probe("https://x.example/")[0] == "BROKEN"


# ---------------------------------------------------------------------- main
def test_a_broken_link_fails_the_check(monkeypatch):
    monkeypatch.setattr(LINKS, "probe", lambda url: ("BROKEN", "HTTP 404"))
    assert LINKS.main() == 1


@pytest.mark.parametrize("status", ["BLOCKED", "PRIVATE"])
def test_unverifiable_links_do_not_fail_but_are_not_reported_as_passing(
        monkeypatch, capsys, status):
    monkeypatch.setattr(LINKS, "probe", lambda url: (status, "cannot see it"))
    assert LINKS.main() == 0
    out = capsys.readouterr().out
    assert "UNVERIFIABLE" in out and "NOT counted as passing" in out
    assert "OK —" not in out          # must never read as a clean pass


def test_all_auth_is_a_pass_with_the_limit_stated(monkeypatch, capsys):
    monkeypatch.setattr(LINKS, "probe", lambda url: ("AUTH", "HTTP 403"))
    assert LINKS.main() == 0
    out = capsys.readouterr().out
    assert "none provably broken" in out
    assert "not proof the page is the right one" in out


def test_an_empty_link_table_errors_rather_than_passing(monkeypatch):
    monkeypatch.setattr(LINKS, "urls_in_section", lambda text: [])
    assert LINKS.main() == 2


def test_a_missing_deploy_doc_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(LINKS, "DEPLOY_DOC", tmp_path / "gone.md")
    assert LINKS.main() == 2
