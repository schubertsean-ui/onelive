"""Unit tests for the deterministic Eventbrite importer
(worker/importers/{domain_map.eventbrite_domain, normalize.normalize_eventbrite,
eventbrite.fetch_known}). No network, no DB — inline fixtures + monkeypatch only,
so this proves the mapping/normalization/paging WITHOUT a live token.

The inline event is modeled on the documented Eventbrite API v3 event shape with
expand=venue,ticket_availability,category,subcategory. It is replaced with a
captured live payload once the founder-crucial EVENTBRITE_TOKEN lands (the shapes
asserted here fail loudly if the real payload drifts).
"""
from worker.importers.domain_map import DOMAINS, eventbrite_domain, unmapped
from worker.importers.normalize import normalize_eventbrite


# ---- domain_map: eventbrite_domain -------------------------------------------

def test_eb_top_categories_map_to_domains():
    assert eventbrite_domain("Music", None)[0] == "live-music"
    assert eventbrite_domain("Business", None)[0] == "ideas"
    assert eventbrite_domain("Food & Drink", None)[0] == "food-drink"
    assert eventbrite_domain("Community & Culture", None)[0] == "community"
    assert eventbrite_domain("Film Media & Entertainment", None)[0] == "film"
    assert eventbrite_domain("Sports & Fitness", None)[0] == "sports"
    assert eventbrite_domain("Health", None)[0] == "wellness"
    assert eventbrite_domain("Science & Technology", None)[0] == "ideas"
    assert eventbrite_domain("Charity & Causes", None)[0] == "community"
    assert eventbrite_domain("Religion", None)[0] == "heritage"
    assert eventbrite_domain("Family & Education", None)[0] == "family"
    assert eventbrite_domain("Seasonal", None)[0] == "seasonal"
    assert eventbrite_domain("Fashion", None)[0] == "fashion-design"
    assert eventbrite_domain("Home & Lifestyle", None)[0] == "place-based"
    assert eventbrite_domain("Hobbies", None)[0] == "fairs-expos"


def test_eb_performing_visual_arts_refined_by_subcategory():
    # The broad "Performing & Visual Arts" header is refined by the provider's
    # own subcategory — theatre/comedy/dance/opera/fine-art land distinctly.
    assert eventbrite_domain("Performing & Visual Arts", "Theatre")[0] == "theater"
    assert eventbrite_domain("Performing & Visual Arts", "Comedy")[0] == "comedy"
    assert eventbrite_domain("Performing & Visual Arts", "Dance")[0] == "dance"
    assert eventbrite_domain("Performing & Visual Arts", "Opera")[0] == "performing-arts"
    assert eventbrite_domain("Performing & Visual Arts", "Fine Art")[0] == "visual-arts"
    # No/unknown subcategory falls back to the coarse header domain, not UNMAPPED.
    assert eventbrite_domain("Performing & Visual Arts", None)[0] == "performing-arts"


def test_eb_community_refined_by_subcategory():
    assert eventbrite_domain("Community & Culture", "Heritage")[0] == "heritage"
    assert eventbrite_domain("Community & Culture", "State Fair")[0] == "festivals"
    assert eventbrite_domain("Community & Culture", "LGBT")[0] == "community"


def test_eb_other_and_unknown_are_unmapped_not_fabricated():
    # The literal "Other" and categories with no OneLive analogue must surface as
    # 'unmapped', never guessed into a real domain (no fabricated data).
    assert eventbrite_domain("Other", None)[0] == "unmapped"
    assert eventbrite_domain("Government", None)[0] == "unmapped"
    assert eventbrite_domain("Auto Boat & Air", None)[0] == "unmapped"
    assert eventbrite_domain("School Activities", None)[0] == "unmapped"
    assert eventbrite_domain(None, None)[0] == "unmapped"
    assert "UNMAPPED" in unmapped("eventbrite", "Other / None")


def test_eb_placeholder_subcategory_not_shown_as_subsegment():
    # A card must never read "Food & Drink · Other".
    assert eventbrite_domain("Food & Drink", "Other")[1] is None
    assert eventbrite_domain("Food & Drink", "")[1] is None
    # A real subcategory is surfaced verbatim.
    assert eventbrite_domain("Food & Drink", "Beer")[1] == "Beer"


def test_eb_mapped_domains_are_canonical():
    for cat in ["Music", "Business", "Food & Drink", "Community & Culture",
                "Sports & Fitness", "Health", "Seasonal", "Fashion"]:
        d, _ = eventbrite_domain(cat, None)
        assert d in DOMAINS


# ---- normalize_eventbrite ----------------------------------------------------

def _eb_fixture():
    """A documented-shape Eventbrite v3 event (expand=venue,ticket_availability,
    category,subcategory)."""
    return {
        "id": "1234567890",
        "name": {"text": "Austin Food Truck Festival", "html": "Austin Food Truck Festival"},
        "start": {"utc": "2026-08-01T23:00:00Z", "timezone": "America/Chicago"},
        "end": {"utc": "2026-08-02T02:00:00Z", "timezone": "America/Chicago"},
        "url": "https://www.eventbrite.com/e/1234567890",
        "status": "live",
        "is_free": False,
        "ticket_availability": {
            "minimum_ticket_price": {"currency": "USD", "major_value": "15.00", "value": 1500},
            "maximum_ticket_price": {"currency": "USD", "major_value": "45.00", "value": 4500},
        },
        "category": {"name": "Food & Drink"},
        "subcategory": {"name": "Beer"},
        "logo": {"url": "https://img.evbuc.com/logo.jpg"},
        "venue": {
            "name": "Fair Market",
            "address": {
                "city": "Austin",
                "localized_address_display": "1100 E 5th St, Austin, TX 78702",
                "latitude": "30.2626",
                "longitude": "-97.7288",
            },
        },
    }


def test_eb_normalize_roundtrip_maps_fields():
    ev = normalize_eventbrite(_eb_fixture())
    assert ev is not None
    assert ev["source_provider"] == "eventbrite"
    assert ev["external_id"] == "1234567890"
    assert ev["title"] == "Austin Food Truck Festival"
    assert ev["category"] == "food-drink"
    assert ev["subsegment"] == "Beer"
    assert ev["start_time"] == "2026-08-01T23:00:00Z"
    assert ev["end_time"] == "2026-08-02T02:00:00Z"
    assert ev["status"] == "scheduled"
    assert ev["on_sale_status"] == "onsale"
    assert ev["price_min"] == 15.0 and ev["price_max"] == 45.0
    assert ev["currency"] == "USD"
    assert ev["is_free"] is False
    assert ev["ticket_url"] == "https://www.eventbrite.com/e/1234567890"
    assert ev["image_url"] == "https://img.evbuc.com/logo.jpg"
    assert ev["venue_name"] == "Fair Market"
    assert ev["venue_city"] == "Austin"
    assert ev["venue_address"] == "1100 E 5th St, Austin, TX 78702"
    assert ev["venue_lat"] == 30.2626 and ev["venue_lng"] == -97.7288
    assert ev["performer"] is None  # Eventbrite has no performer taxonomy
    assert ev["confidence"] == "confirmed"


def test_eb_free_flag_authoritative_from_provider():
    raw = _eb_fixture()
    raw["is_free"] = True
    raw["ticket_availability"] = {}
    ev = normalize_eventbrite(raw)
    assert ev["is_free"] is True
    assert ev["price_min"] is None and ev["price_max"] is None


def test_eb_cancelled_status_maps_event_status():
    raw = _eb_fixture()
    raw["status"] = "canceled"
    ev = normalize_eventbrite(raw)
    assert ev["status"] == "cancelled"
    assert ev["on_sale_status"] == "cancelled"


def test_eb_unmapped_category_normalizes_honestly():
    raw = _eb_fixture()
    raw["category"] = {"name": "Government"}
    raw["subcategory"] = {"name": "Other"}
    ev = normalize_eventbrite(raw)
    assert ev["category"] == "unmapped"       # honest, not fabricated
    assert ev["subsegment"] is None           # placeholder subcategory suppressed


def test_eb_missing_id_or_title_returns_none():
    assert normalize_eventbrite({"name": {"text": "no id"}}) is None
    assert normalize_eventbrite({"id": "x"}) is None
    assert normalize_eventbrite({"id": "x", "name": {"text": ""}}) is None


# ---- fetch client: pagination + de-dup (no network) --------------------------

def test_fetch_known_follows_continuation_and_dedupes(monkeypatch):
    """fetch_known polls each id, follows Eventbrite's continuation pagination,
    and de-dupes an event surfaced under more than one id — all without network."""
    from worker.importers import eventbrite as eb

    pages = {
        # org "A": two pages via continuation
        (None,): {"events": [{"id": "e1"}],
                  "pagination": {"has_more_items": True, "continuation": "c2"}},
        ("c2",): {"events": [{"id": "e2"}, {"id": "shared"}],
                  "pagination": {"has_more_items": False, "continuation": None}},
        # org "B": one page, re-surfaces "shared"
        (None, "B"): {"events": [{"id": "shared"}, {"id": "e3"}],
                      "pagination": {"has_more_items": False}},
    }
    seen_urls = []

    def fake_get(url, token, timeout=30):
        assert token == "tok"
        seen_urls.append(url)
        if "organizations/A/events" in url:
            cont = "c2" if "continuation=c2" in url else None
            return pages[(cont,)]
        if "organizations/B/events" in url:
            return pages[(None, "B")]
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(eb, "_get", fake_get)
    out = list(eb.fetch_known("tok", ["A", "B"], sleep=0))
    ids = [e["id"] for e in out]

    assert ids.count("shared") == 1               # de-duped across ids
    assert set(ids) == {"e1", "e2", "e3", "shared"}
    # expand + status=live were requested on the polling call
    assert any("expand=" in u and "status=live" in u for u in seen_urls)


def test_fetch_known_fails_loud_without_token(monkeypatch):
    from worker.importers import eventbrite as eb
    monkeypatch.delenv("EVENTBRITE_TOKEN", raising=False)
    try:
        list(eb.fetch_known(None, ["A"]))
    except RuntimeError as e:
        assert "EVENTBRITE_TOKEN" in str(e)
    else:
        raise AssertionError("expected RuntimeError on missing token")
