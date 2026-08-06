"""Pure-function tests for the source scanner v1 (tools/scan_new_sources.py).

No network: the domain normalization, catalog diff, and platform filter decide
WHAT counts as a new source candidate — pinned here.
"""
from tools.scan_new_sources import catalog_domains, is_platform, norm_domain


def test_norm_domain_strips_www_and_lowercases():
    assert norm_domain("https://WWW.TheSaxonPub.com/shows") == "thesaxonpub.com"
    assert norm_domain("http://mohawkaustin.com/") == "mohawkaustin.com"
    assert norm_domain("not a url") is None


def test_catalog_domains_reads_base_urls():
    cat = [{"base_url": "https://www.mohawkaustin.com/"},
           {"base_url": None}, {"name": "no url"}]
    assert catalog_domains(cat) == {"mohawkaustin.com"}


def test_platform_domains_are_never_candidates():
    assert is_platform("facebook.com")
    assert is_platform("m.facebook.com")
    assert is_platform("linktr.ee")
    # A venue named like a platform is NOT filtered.
    assert not is_platform("facebookbar.com")
    assert not is_platform("thesaxonpub.com")


def test_query_pack_covers_every_canonical_domain():
    # Sentinel (founder 2026-08-05, "it's at least 23 … where are you getting
    # all this?"): the v1 pack was an ad-hoc 20-phrase list with whole
    # canonical domains missing. The pack is now DERIVED from the canonical
    # taxonomy, and this test makes a new canonical domain FAIL the suite
    # until the scanner covers it — under-coverage cannot recur silently.
    from tools.scan_new_sources import DOMAIN_QUERY_PACK
    from worker.importers.domain_map import DOMAINS

    assert set(DOMAIN_QUERY_PACK) == set(DOMAINS)
    assert all(len(v) >= 2 for v in DOMAIN_QUERY_PACK.values()), \
        "every domain needs at least two plain search phrases"


def test_full_capcog_sweep_composition():
    # Launch directive (founder, verbatim): "all the data at launch: full
    # CAPCOG sweep". The sweep must be cities x phrases, Austin-first but
    # region-wide, and its size must stay within one dispatch's declared
    # bound so the launch run needs no silent truncation.
    from tools.scan_new_sources import CAPCOG_CITIES, QUERY_PACK

    assert CAPCOG_CITIES[0] == "Austin"
    assert len(CAPCOG_CITIES) >= 20  # the region, not the city
    sweep = len(CAPCOG_CITIES) * len(QUERY_PACK)
    assert 800 <= sweep <= 1000, sweep


def test_festival_windows_file_parses_and_is_dated():
    import json

    data = json.load(open("sources/festival_windows.json"))
    for w in data["windows"]:
        assert w["starts"] <= w["ends"]
        for key in ("slug", "name", "geo", "keyword_pack"):
            assert w.get(key)


def test_festival_phase_boundaries():
    # The founder's "define this" answer (decision record
    # 2026-08-05_festival-window-phases.md): every boundary day pinned so a
    # band cannot drift silently. rampup = starts-28..starts-1, live =
    # starts..ends, winddown = ends+1, else off.
    import datetime

    from tools.festival_phase import phase_for

    w = {"slug": "t", "starts": "2026-10-02", "ends": "2026-10-11"}
    d = datetime.date.fromisoformat
    assert phase_for(w, d("2026-09-03")) == "off"      # rampup-1
    assert phase_for(w, d("2026-09-04")) == "rampup"   # starts-28
    assert phase_for(w, d("2026-10-01")) == "rampup"   # starts-1
    assert phase_for(w, d("2026-10-02")) == "live"     # starts
    assert phase_for(w, d("2026-10-11")) == "live"     # ends
    assert phase_for(w, d("2026-10-12")) == "winddown" # ends+1
    assert phase_for(w, d("2026-10-13")) == "off"      # winddown+1


def test_festival_phase_overrides_are_data():
    import datetime

    from tools.festival_phase import phase_for

    w = {"slug": "t", "starts": "2026-10-02", "ends": "2026-10-11",
         "rampup_days": 7, "winddown_days": 2}
    d = datetime.date.fromisoformat
    assert phase_for(w, d("2026-09-24")) == "off"
    assert phase_for(w, d("2026-09-25")) == "rampup"
    assert phase_for(w, d("2026-10-13")) == "winddown"
    assert phase_for(w, d("2026-10-14")) == "off"


def test_festival_phase_resolve_modes():
    # full supersedes but keyword sweeps STILL run for live windows (the
    # domain pack never queries festival terms); shoulders are keyword-only;
    # nothing active = honest 'no'.
    import datetime

    from tools.festival_phase import resolve

    live_w = {"slug": "live-fest", "starts": "2026-10-02", "ends": "2026-10-11"}
    ramp_w = {"slug": "ramp-fest", "starts": "2026-10-23", "ends": "2026-10-25"}
    today = datetime.date.fromisoformat("2026-10-05")
    plan = resolve([live_w, ramp_w], today)
    assert plan["mode"] == "full"
    assert plan["full"] == ["live-fest"]
    assert set(plan["keyword"]) == {"live-fest", "ramp-fest"}

    plan = resolve([ramp_w], today)  # only a rampup window
    assert plan["mode"] == "keyword"
    assert plan["full"] == []
    assert plan["keyword"] == ["ramp-fest"]

    plan = resolve([live_w], datetime.date.fromisoformat("2026-12-01"))
    assert plan["mode"] == "no"


def test_festival_keyword_sweep_composition(monkeypatch, capsys):
    # --festival runs the window's keyword_pack against its geo — a handful
    # of targeted queries, never the 968-query full sweep.
    import json

    import tools.scan_new_sources as scan

    seen = []

    def fake_search(q, count=20):
        seen.append(q)
        return {"web": {"results": [
            {"url": "https://aclpopups.com/party", "title": "ACL pop up",
             "description": ""}]}}

    monkeypatch.setattr(scan, "api_key", lambda: "k")
    monkeypatch.setattr(scan, "search", fake_search)
    rc = scan.main(["--festival", "acl-2026"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["festival"] == "acl-2026"
    assert out["cities"] == ["Austin"]
    windows = json.load(open("sources/festival_windows.json"))["windows"]
    pack = next(w for w in windows if w["slug"] == "acl-2026")["keyword_pack"]
    assert len(seen) == len(pack)
    assert all(q.startswith("Austin ") for q in seen)
    assert [c["domain"] for c in out["new_domain_candidates"]] == ["aclpopups.com"]


def test_festival_unknown_slug_fails_loud(monkeypatch):
    import tools.scan_new_sources as scan

    monkeypatch.setattr(scan, "api_key", lambda: "k")
    assert scan.main(["--festival", "not-a-window"]) == 2
