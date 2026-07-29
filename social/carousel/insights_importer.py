"""Meta Insights → PostMetrics: the measure half of the learning loop (spec §6, §9.1).

Greppable summary: turns Meta Insights data into the PostMetrics rows that
agent_loop.ingest_results() folds into the ledger and the bandit. Two paths,
one importer (spec §9.1: "metrics ingestion takes exported JSON meanwhile"):
  - PURE PARSE (no credentials, works today): map an Insights JSON payload —
    exported by hand or returned by the API — onto a validated PostMetrics.
  - LIVE FETCH (credential-gated, fail-closed OFF): pull a post's insights
    from the Graph API. Off unless META_ACCESS_TOKEN is present, exactly like
    the posting client.

North-star integrity is preserved here, not eroded: PostMetrics.unique_interactions
is UNIQUE interacting accounts (the interaction-rate denominator is reach, so the
numerator must be accounts, not total actions). Meta's per-media `total_interactions`
counts actions (likes+saves+comments+shares) and can exceed reach on a viral post,
so this importer NEVER silently maps it onto unique_interactions — it requires a
genuine unique-accounts metric (`accounts_engaged`, or an explicit `unique_interactions`)
and fails loud if neither is present, rather than reporting a rate that overstates
engagement. The metric-name fidelity across Meta API versions is tracked as R-061.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from social.carousel.metrics import PostMetrics

ACCESS_TOKEN_ENV = "META_ACCESS_TOKEN"
GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# The insights metrics this importer reads, in the API's request order.
INSIGHTS_METRICS = (
    "reach",
    "accounts_engaged",
    "saved",
    "shares",
    "comments",
    "likes",
    "profile_visits",
    "follows",
    "views",
)

# Meta insights metric name -> PostMetrics field. Aliases (both a metric and
# its historical/alternate name) map to the same field; the first present wins.
_FIELD_FROM_METRIC = {
    "reach": "reach",
    "accounts_engaged": "unique_interactions",
    "unique_interactions": "unique_interactions",
    "saved": "saves",
    "saves": "saves",
    "shares": "shares",
    "comments": "comments",
    "likes": "likes",
    "profile_visits": "profile_visits",
    "profile_activity": "profile_visits",
    "follows": "follows",
    "follower_count": "follows",
    "views": "impressions",
    "impressions": "impressions",
    "link_clicks": "link_clicks",
    "website_clicks": "link_clicks",
}


class InsightsImportError(ValueError):
    """An insights payload cannot be turned into a trustworthy PostMetrics."""


class MetaConfigError(RuntimeError):
    """Live insights fetch is not configured — fail closed OFF."""


def insights_import_enabled() -> bool:
    """Live-fetch capability: on only when the access token is present."""
    return bool(os.environ.get(ACCESS_TOKEN_ENV, "").strip())


def parse_insights(payload) -> dict[str, int]:
    """Flatten a Meta Insights response into {metric_name: int value}. Handles
    both response shapes: the classic `values:[{value:...}]` series and the
    newer `total_value:{value:...}`. A payload may be the full response
    ({"data": [...]}) or the bare data list. Non-integer or negative values
    fail loud — a metric is a count."""
    if isinstance(payload, dict):
        entries = payload.get("data", payload)
    else:
        entries = payload
    if not isinstance(entries, list):
        raise InsightsImportError(
            f"insights payload is not a metric list (got {type(entries).__name__})"
        )
    out: dict[str, int] = {}
    for entry in entries:
        if not isinstance(entry, dict) or "name" not in entry:
            raise InsightsImportError(f"malformed insights entry: {entry!r}")
        name = entry["name"]
        if "total_value" in entry and isinstance(entry["total_value"], dict):
            raw = entry["total_value"].get("value")
        else:
            values = entry.get("values") or []
            if not values or not isinstance(values[0], dict):
                raise InsightsImportError(f"insights metric {name!r} has no value")
            raw = values[0].get("value")
        if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
            raise InsightsImportError(
                f"insights metric {name!r} value {raw!r} is not a non-negative integer"
            )
        out[name] = raw
    return out


def post_metrics_from_insights(
    *,
    post_id: str,
    surface: str,
    tier: str,
    posted_at: str,
    payload,
) -> PostMetrics:
    """Build a validated PostMetrics from an insights payload. posted_at comes
    from the platform record and is passed through untouched (never generated).
    Requires reach and a genuine unique-accounts engagement metric; fails loud
    otherwise so the ledger never records a north-star rate it cannot defend."""
    if not post_id or not surface or not tier or not posted_at:
        raise InsightsImportError("post_id, surface, tier, and posted_at are all required")
    raw = parse_insights(payload)

    fields: dict[str, int] = {}
    for metric, value in raw.items():
        field = _FIELD_FROM_METRIC.get(metric)
        if field is None:
            continue  # an unknown metric is ignored, never silently miscounted
        # First present alias wins; a later alias never overwrites it.
        fields.setdefault(field, value)

    if "reach" not in fields:
        raise InsightsImportError(
            "insights payload has no `reach` — the interaction-rate denominator "
            "is missing, refusing to record a rate we cannot compute"
        )
    if "unique_interactions" not in fields:
        raise InsightsImportError(
            "insights payload has no unique-accounts engagement metric "
            "(`accounts_engaged` or `unique_interactions`) — refusing to "
            "substitute `total_interactions`, which counts actions not accounts "
            "and would overstate the north-star rate"
        )
    metrics = PostMetrics(post_id=post_id, surface=surface, tier=tier, posted_at=posted_at, **fields)
    metrics.validate()
    return metrics


def import_exported_metrics(json_str: str, known_post_ids) -> list[PostMetrics]:
    """The credential-free path (spec §9.1): read a list of exported records,
    each {post_id, surface, tier, posted_at, insights: <payload>}, into
    validated PostMetrics. One malformed record fails the whole import loud.

    known_post_ids (evaluator PR #106) is the REQUIRED allowlist of post ids
    OneLive actually published (from the release/publish record). Every record's
    post_id must be a member, or the import refuses — hand-authored JSON cannot
    fabricate metrics for an arbitrary post and have the learning loop trust them
    as real public outcomes. An empty allowlist means nothing can be imported
    (fail-closed), never "trust everything"."""
    known = set(known_post_ids or ())
    if not known:
        raise InsightsImportError(
            "no known published-post ids supplied — exported metrics cannot be "
            "bound to real posts, refusing (fail-closed; pass the publish "
            "record's post ids)"
        )
    try:
        records = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise InsightsImportError(f"exported metrics are not valid JSON: {exc}") from exc
    if not isinstance(records, list):
        raise InsightsImportError("exported metrics must be a JSON list of records")
    out: list[PostMetrics] = []
    for i, record in enumerate(records):
        if not isinstance(record, dict) or "insights" not in record:
            raise InsightsImportError(f"exported record {i} is missing an `insights` payload")
        post_id = record.get("post_id", "")
        if post_id not in known:
            raise InsightsImportError(
                f"exported record {i} post_id {post_id!r} is not a known "
                "published post — refusing to trust unbound metrics"
            )
        out.append(
            post_metrics_from_insights(
                post_id=post_id,
                surface=record.get("surface", ""),
                tier=record.get("tier", ""),
                posted_at=record.get("posted_at", ""),
                payload=record["insights"],
            )
        )
    return out


def _urllib_transport(url: str, headers: dict) -> dict:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise MetaConfigError(f"Insights HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise MetaConfigError(f"Insights transport error: {exc.reason}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise InsightsImportError(f"Insights returned non-JSON: {body[:200]!r}") from exc


def fetch_and_import(
    *,
    post_id: str,
    surface: str,
    tier: str,
    posted_at: str,
    known_post_ids,
    transport=None,
) -> PostMetrics:
    """Live path: pull a post's insights from the Graph API and import them.
    Fail-closed OFF — refuses without META_ACCESS_TOKEN. Like the exported path
    (evaluator PR #106 r5), the post_id must be a member of the known
    published-post allowlist — metrics from an arbitrary Meta post are never
    recorded as OneLive carousel performance. The transport is injectable for
    hermetic tests; the real urllib GET is the default."""
    known = set(known_post_ids or ())
    if post_id not in known:
        raise InsightsImportError(
            f"post_id {post_id!r} is not a known OneLive-published post — "
            "refusing to record metrics for an unbound post"
        )
    token = os.environ.get(ACCESS_TOKEN_ENV, "").strip()
    if not token:
        raise MetaConfigError(
            f"{ACCESS_TOKEN_ENV} unset — live insights fetch is fail-closed OFF. "
            "Use import_exported_metrics() for the credential-free path."
        )
    fetch = transport or _urllib_transport
    # Token in the Authorization header, not the query string (evaluator PR #106
    # nit): a bearer header is far less likely to be captured in access logs or
    # referrers than a token baked into the URL.
    query = urllib.parse.urlencode({"metric": ",".join(INSIGHTS_METRICS)})
    # Quote post_id into the path (evaluator PR #106 nit): defend against
    # unexpected characters even though it is a numeric Meta id in practice.
    safe_id = urllib.parse.quote(str(post_id), safe="")
    url = f"{GRAPH_API_BASE}/{safe_id}/insights?{query}"
    payload = fetch(url, {"Authorization": f"Bearer {token}"})
    return post_metrics_from_insights(
        post_id=post_id, surface=surface, tier=tier, posted_at=posted_at, payload=payload
    )
