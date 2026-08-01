"""Safety-property tests for the SCA exception gate (tools/sca_gate.py).

These prove the load-bearing guarantees of the managed-exception mechanism
(docs/EXTERNAL_FINDINGS_POLICY.md): an unlisted finding blocks; an exception
holds ONLY while genuinely unfixable and unexpired; and any malformation fails
CLOSED. Everything runs on in-memory fixtures — no npm, no network.
"""
import datetime as dt
import json

import pytest

from tools import sca_gate


TODAY = dt.date(2026, 7, 24)


def _audit(*nodes):
    """Build a minimal `npm audit --json` document from (name, severity,
    ghsa, fixAvailable) tuples. A ghsa of None makes a transitive string via."""
    vulns = {}
    for name, severity, ghsa, fix in nodes:
        via = (
            [{"severity": severity, "url": f"https://github.com/advisories/{ghsa}",
              "title": f"{name} issue"}]
            if ghsa
            else ["some-root-package"]
        )
        if name in vulns:
            # Faithful to real `npm audit`: ONE node per package carrying MANY
            # advisories in its `via` list (the live audit reports postcss with
            # three). Repeating a package name APPENDS rather than overwrites —
            # overwriting silently hid every advisory but the last.
            vulns[name]["via"].extend(via)
            vulns[name]["fixAvailable"] = vulns[name]["fixAvailable"] or fix
        else:
            vulns[name] = {"severity": severity, "via": list(via), "fixAvailable": fix}
    return {"vulnerabilities": vulns}


def _allowlist(tmp_path, *entries):
    p = tmp_path / "allow.json"
    p.write_text(json.dumps({"entries": list(entries)}))
    return p


def _entry(package, ghsa, expires="2026-08-24", severity="high"):
    return {
        "package": package,
        "ghsa": ghsa,
        "severity": severity,
        "expires": expires,
        "owner": "test",
        "added": "2026-07-24",
        "no_fix_reason": "no released upstream fix (test)",
        "operational_exposure": "not reachable in our usage (test)",
        "resolution_trigger": "upstream ships a fix (test)",
    }


def _run(doc, allowlist_path, today=TODAY):
    al = sca_gate._load_allowlist(allowlist_path, today)
    return sca_gate.evaluate(doc, al, today)


def test_unlisted_high_advisory_fails(tmp_path):
    doc = _audit(("postcss", "high", "GHSA-xxxx", False))
    ok, lines = _run(doc, _allowlist(tmp_path))  # empty allowlist
    assert ok is False
    assert any("UNLISTED" in l for l in lines)


def test_listed_unexpired_nofix_is_suppressed(tmp_path):
    doc = _audit(("postcss", "high", "GHSA-6g55", False))
    ok, lines = _run(doc, _allowlist(tmp_path, _entry("postcss", "GHSA-6g55")))
    assert ok is True
    assert any("SUPPRESSED" in l for l in lines)


def test_expired_entry_fails(tmp_path):
    doc = _audit(("postcss", "high", "GHSA-6g55", False))
    al = _allowlist(tmp_path, _entry("postcss", "GHSA-6g55", expires="2026-07-01"))
    ok, lines = _run(doc, al)
    assert ok is False
    assert any("EXPIRED" in l for l in lines)


def test_fix_now_available_auto_reblocks(tmp_path):
    # The advisory is still listed, unexpired — but a fix now exists, so the
    # exception must NOT hold (anti-rot: upgrade instead of suppressing).
    doc = _audit(("postcss", "high", "GHSA-6g55", {"name": "postcss", "version": "8.5.12"}))
    ok, lines = _run(doc, _allowlist(tmp_path, _entry("postcss", "GHSA-6g55")))
    assert ok is False
    assert any("FIX NOW AVAILABLE" in l for l in lines)

    # fixAvailable: true likewise re-blocks.
    doc2 = _audit(("postcss", "high", "GHSA-6g55", True))
    ok2, _ = _run(doc2, _allowlist(tmp_path, _entry("postcss", "GHSA-6g55")))
    assert ok2 is False


def test_transitive_only_node_needs_no_own_entry(tmp_path):
    # `next` is flagged high but only via string references to its roots; once
    # the roots are suppressed, next imposes no additional requirement.
    doc = _audit(
        ("next", "high", None, False),
        ("postcss", "high", "GHSA-6g55", False),
    )
    ok, _ = _run(doc, _allowlist(tmp_path, _entry("postcss", "GHSA-6g55")))
    assert ok is True


def test_stale_entry_fails(tmp_path):
    # An allowlist entry for an advisory that is NOT in the current audit is
    # stale and must FAIL — forcing its deletion once the vuln is fixed/gone.
    doc = _audit(("postcss", "high", "GHSA-6g55", False))
    al = _allowlist(
        tmp_path,
        _entry("postcss", "GHSA-6g55"),
        _entry("leftpad", "GHSA-gone-1234"),  # not present in the audit
    )
    ok, lines = _run(doc, al)
    assert ok is False
    assert any("STALE" in l for l in lines)


def test_moderate_below_threshold_passes(tmp_path):
    doc = _audit(("postcss", "moderate", "GHSA-moderate", False))
    ok, lines = _run(doc, _allowlist(tmp_path))  # not even listed
    assert ok is True


def test_malformed_allowlist_fails_closed(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not json ")
    with pytest.raises(sca_gate.GateError):
        sca_gate._load_allowlist(bad, TODAY)


def test_entry_missing_field_fails_closed(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"entries": [{"package": "postcss"}]}))  # no ghsa/expires/owner
    with pytest.raises(sca_gate.GateError):
        sca_gate._load_allowlist(p, TODAY)


def test_duplicate_entry_fails_closed(tmp_path):
    al = _allowlist(
        tmp_path,
        _entry("postcss", "GHSA-6g55", expires="2026-08-24"),
        _entry("postcss", "GHSA-6g55", expires="2027-01-01"),  # dup, longer expiry
    )
    with pytest.raises(sca_gate.GateError):
        sca_gate._load_allowlist(al, TODAY)


def test_entry_bad_date_fails_closed(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"entries": [_entry("postcss", "GHSA-6g55", expires="soon")]}))
    with pytest.raises(sca_gate.GateError):
        sca_gate._load_allowlist(p, TODAY)


def test_malformed_audit_shapes_fail_closed():
    good = _audit(("postcss", "high", "GHSA-6g55", False))
    sca_gate._validate_audit_shape(good)  # valid — no raise

    bad_docs = [
        {"vulnerabilities": {"x": "not-an-object"}},
        {"vulnerabilities": {"x": {"via": "not-a-list"}}},
        {"vulnerabilities": {"x": {"severity": "high", "via": [123]}}},
        # high advisory with no url -> cannot identify (GHSA)
        {"vulnerabilities": {"x": {"via": [{"severity": "high", "title": "t"}], "fixAvailable": False}}},
        # blocking direct advisory but missing fixAvailable
        {"vulnerabilities": {"x": {"via": [{"severity": "high", "url": "a/GHSA-z"}]}}},
    ]
    for doc in bad_docs:
        with pytest.raises(sca_gate.GateError):
            sca_gate._validate_audit_shape(doc)


def test_unparseable_audit_fails_closed(tmp_path):
    bad = tmp_path / "audit.txt"
    bad.write_text("npm ERR! network timeout")

    class _Args:
        audit_json = str(bad)
        web_dir = "web"

    with pytest.raises(sca_gate.GateError):
        sca_gate._load_audit(_Args())


def test_end_to_end_main_passes_on_real_shape(tmp_path, capsys):
    doc = _audit(
        ("next", "high", None, False),
        ("postcss", "high", "GHSA-6g55", False),
        ("sharp", "high", "GHSA-f88m", False),
    )
    audit_p = tmp_path / "audit.json"
    audit_p.write_text(json.dumps(doc))
    al = _allowlist(tmp_path, _entry("postcss", "GHSA-6g55"), _entry("sharp", "GHSA-f88m"))
    rc = sca_gate.main(
        ["--audit-json", str(audit_p), "--allowlist", str(al), "--today", "2026-07-24"]
    )
    assert rc == 0
    assert "PASS" in capsys.readouterr().out


def test_the_shipped_allowlist_covers_current_audit(tmp_path):
    """The real committed allowlist must actually clear the current committed
    audit shape, or CI is red-by-construction.

    As of 2026-07-31 the postcss/sharp advisories that previously required
    exceptions were REMOVED from the tree at the root: web/package.json pins
    `overrides` forcing postcss >= 8.5.12 and sharp >= 0.35.0, so the patched
    packages resolve and `npm audit --omit=dev` reports zero high/critical
    advisories. The shipped allowlist is therefore empty — no live advisory to
    suppress, and (by the gate's anti-rot rule) no stale entry left behind. This
    pins that post-fix invariant: a clean audit + an empty allowlist PASSES, and
    the allowlist carries no exceptions that would go stale against a clean audit.
    """
    al = sca_gate._load_allowlist(sca_gate._DEFAULT_ALLOWLIST, TODAY)
    assert al == {}, (
        "shipped SCA allowlist must be empty now that postcss/sharp are patched "
        f"via overrides — found stale exceptions: {sorted(al)}"
    )
    # A clean production audit (the reality after the override upgrade) passes
    # with the empty allowlist and produces no findings.
    clean = _audit(("next", "high", None, False))  # transitive-only, no direct advisory
    ok, lines = sca_gate.evaluate(clean, al, TODAY)
    assert ok is True, "\n".join(lines)
