"""Insights → PostMetrics: both response shapes, north-star integrity, fail-closed live path."""
from __future__ import annotations

import json

import pytest

from social.carousel.metrics import PostMetrics
import social.carousel.insights_importer as importer
from social.carousel.insights_importer import (
    InsightsImportError,
    MetaConfigError,
    fetch_and_import,
    import_exported_metrics,
    parse_insights,
    post_metrics_from_insights,
)


def _values_payload(**metrics):
    return {"data": [{"name": n, "values": [{"value": v}]} for n, v in metrics.items()]}


def _total_value_payload(**metrics):
    return {"data": [{"name": n, "total_value": {"value": v}} for n, v in metrics.items()]}


def test_parse_values_shape():
    parsed = parse_insights(_values_payload(reach=1000, saved=40, shares=12))
    assert parsed == {"reach": 1000, "saved": 40, "shares": 12}


def test_parse_total_value_shape():
    parsed = parse_insights(_total_value_payload(reach=500, accounts_engaged=120))
    assert parsed == {"reach": 500, "accounts_engaged": 120}


def test_parse_accepts_bare_list():
    parsed = parse_insights([{"name": "reach", "values": [{"value": 7}]}])
    assert parsed == {"reach": 7}


@pytest.mark.parametrize("bad", [-1, 3.5, True, "40", None])
def test_parse_rejects_non_count_values(bad):
    with pytest.raises(InsightsImportError):
        parse_insights({"data": [{"name": "reach", "values": [{"value": bad}]}]})


def test_post_metrics_maps_and_validates():
    payload = _values_payload(
        reach=2000, accounts_engaged=350, saved=80, shares=25,
        comments=10, likes=200, profile_visits=15, follows=6, views=5200,
    )
    m = post_metrics_from_insights(
        post_id="p1", surface="instagram_feed", tier="T1",
        posted_at="2026-07-28T09:00:00-05:00", payload=payload,
    )
    assert isinstance(m, PostMetrics)
    assert m.reach == 2000
    assert m.unique_interactions == 350  # accounts_engaged -> unique accounts
    assert m.saves == 80 and m.shares == 25 and m.impressions == 5200
    assert m.interaction_rate == pytest.approx(0.175)


def test_explicit_unique_interactions_alias_works():
    payload = _values_payload(reach=100, unique_interactions=20)
    m = post_metrics_from_insights(
        post_id="p", surface="instagram_feed", tier="T1",
        posted_at="2026-07-28T09:00:00-05:00", payload=payload,
    )
    assert m.unique_interactions == 20


def test_missing_reach_fails_loud():
    with pytest.raises(InsightsImportError):
        post_metrics_from_insights(
            post_id="p", surface="instagram_feed", tier="T1",
            posted_at="2026-07-28T09:00:00-05:00",
            payload=_values_payload(accounts_engaged=10),
        )


def test_total_interactions_is_never_substituted_for_unique():
    # total_interactions (actions, can exceed reach) must NOT become the
    # north-star numerator — the importer refuses rather than overstate.
    with pytest.raises(InsightsImportError):
        post_metrics_from_insights(
            post_id="p", surface="instagram_feed", tier="T1",
            posted_at="2026-07-28T09:00:00-05:00",
            payload=_values_payload(reach=100, total_interactions=250),
        )


def test_unique_exceeding_reach_is_rejected_by_validate():
    with pytest.raises(ValueError):
        post_metrics_from_insights(
            post_id="p", surface="instagram_feed", tier="T1",
            posted_at="2026-07-28T09:00:00-05:00",
            payload=_values_payload(reach=100, accounts_engaged=101),
        )


def test_import_exported_metrics_round_trip():
    records = [
        {
            "post_id": "p1", "surface": "instagram_feed", "tier": "T1",
            "posted_at": "2026-07-28T09:00:00-05:00",
            "insights": _values_payload(reach=800, accounts_engaged=100),
        },
        {
            "post_id": "p2", "surface": "instagram_feed", "tier": "T2",
            "posted_at": "2026-07-28T18:00:00-05:00",
            "insights": _total_value_payload(reach=1200, accounts_engaged=240),
        },
    ]
    out = import_exported_metrics(json.dumps(records), known_post_ids={"p1", "p2"})
    assert [m.post_id for m in out] == ["p1", "p2"]
    assert out[1].interaction_rate == pytest.approx(0.2)


def test_import_exported_metrics_rejects_missing_insights():
    with pytest.raises(InsightsImportError):
        import_exported_metrics(json.dumps([{"post_id": "p"}]), known_post_ids={"p"})


def test_import_exported_metrics_rejects_unknown_post_id():
    # A fabricated record for a post OneLive never published is refused, so the
    # learning loop can't be poisoned by hand-authored metrics.
    records = [{
        "post_id": "not-a-real-post", "surface": "instagram_feed", "tier": "T1",
        "posted_at": "2026-07-28T09:00:00-05:00",
        "insights": _values_payload(reach=800, accounts_engaged=100),
    }]
    with pytest.raises(InsightsImportError):
        import_exported_metrics(json.dumps(records), known_post_ids={"p1"})


def test_import_exported_metrics_empty_allowlist_refuses():
    with pytest.raises(InsightsImportError):
        import_exported_metrics(json.dumps([]), known_post_ids=set())


def test_live_fetch_disabled_without_token(monkeypatch):
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)
    assert importer.insights_import_enabled() is False
    with pytest.raises(MetaConfigError):
        fetch_and_import(
            post_id="p", surface="instagram_feed", tier="T1",
            posted_at="2026-07-28T09:00:00-05:00", known_post_ids={"p"},
        )


def test_live_fetch_rejects_unknown_post_id(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "founder-minted-token")
    with pytest.raises(InsightsImportError):
        fetch_and_import(
            post_id="not-ours", surface="instagram_feed", tier="T1",
            posted_at="2026-07-28T09:00:00-05:00", known_post_ids={"p1"},
            transport=lambda url, headers: _values_payload(reach=1, accounts_engaged=1),
        )


def test_live_fetch_with_injected_transport(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "founder-minted-token")
    seen = {}

    def transport(url, headers):
        seen["url"] = url
        seen["headers"] = headers
        return _values_payload(reach=900, accounts_engaged=180)

    m = fetch_and_import(
        post_id="17900000000000000", surface="instagram_feed", tier="T1",
        posted_at="2026-07-28T09:00:00-05:00", known_post_ids={"17900000000000000"},
        transport=transport,
    )
    assert m.reach == 900 and m.unique_interactions == 180
    assert "17900000000000000/insights" in seen["url"]
    assert "reach" in seen["url"] and "accounts_engaged" in seen["url"]
    # The token rides an Authorization header, never the URL (log-leak nit).
    assert "access_token" not in seen["url"]
    assert seen["headers"]["Authorization"] == "Bearer founder-minted-token"
