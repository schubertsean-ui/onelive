"""SYNTHETIC example events for rendering demonstration carousels.

Greppable summary: every event here is FICTIONAL — invented artists,
invented venues, plausible Austin shapes — used ONLY to demonstrate the
five founder-directed scenario carousels (docs/strategy/
ONE_LIVE_CAROUSEL_EXAMPLES_v1.md) and to regression-test the scenario
path end-to-end. Nothing in this module may ever reach a production
carousel: the `source` field is the sentinel "SYNTHETIC-EXAMPLE", and
tests pin that the sentinel never appears in DOMAIN production config.
The `origin` marker is set so the fixtures can flow through the engine's
canonical-origin check in tests — that marker is a statement about the
READ PATH in production, and these fixtures exist precisely to exercise
it hermetically.

Reference moment for all examples: Friday 2026-07-24, 4:00 pm Austin time
("2026-07-24T16:00:00-05:00") — so Tonight = this evening, Today = the
rest of Friday, This weekend = Fri Jul 24 - Sun Jul 26.
"""

EXAMPLE_REFERENCE_TIME = "2026-07-24T16:00:00-05:00"

_BASE = dict(
    confidence="confirmed",
    event_status="scheduled",
    origin="canonical_event",
    source="SYNTHETIC-EXAMPLE",
)


def _ev(i, name, venue, start, domain, price, image="", **over):
    event = dict(
        _BASE,
        event_id=f"ex-{i}",
        name=name,
        venue_name=venue,
        start_time=start,
        domain_id=domain,
        price_min=price,
        image_url=image or f"https://img.example/ex-{i}.jpg",
    )
    event.update(over)
    return event


EXAMPLE_EVENTS = [
    # --- live music / nightlife / dance (tonight) ------------------------------
    _ev(1, "The Midnight Brass", "Red River Room", "2026-07-24T21:00:00-05:00", "live-music", 15,
        foundry_descriptor={"text": "Horns that start a party", "provenance": "foundry:example:001"}),
    _ev(2, "Casa de Cumbia", "La Esquina Patio", "2026-07-24T22:00:00-05:00", "live-music", 0,
        foundry_descriptor={"text": "Cumbia until the lights come up", "provenance": "foundry:example:002"}),
    _ev(3, "DJ Meridian: Motown to House", "The Basement Line", "2026-07-24T22:30:00-05:00", "nightlife", 5),
    _ev(4, "Two-Step Tuesday's Friday Edition", "Broken Wheel Hall", "2026-07-24T20:00:00-05:00", "dance", 10),
    _ev(5, "Soul Kitchen Revue", "The Velvet Note", "2026-07-24T21:30:00-05:00", "live-music", 20,
        confidence="likely"),
    _ev(6, "Salsa Social + Beginner Lesson", "Plaza Azul", "2026-07-24T20:30:00-05:00", "dance", 0),
    _ev(7, "Analog Synth Night", "Circuit Chapel", "2026-07-24T23:00:00-05:00", "nightlife", 12),
    # --- date-night registers (tonight, later starts) --------------------------
    _ev(8, "Rooftop Strings: Duo Luna", "The Perch at 6th", "2026-07-24T20:00:00-05:00", "performing-arts", 25),
    _ev(9, "Candlelit Standards", "The Velvet Note", "2026-07-24T23:30:00-05:00", "live-music", 30),
    _ev(10, "Late Bites & Bossa Nova", "Verdine's Courtyard", "2026-07-24T21:00:00-05:00", "food-drink", 0),
    _ev(11, "Two-Hander: 'The Lighthouse Keepers'", "Pocket Stage ATX", "2026-07-24T20:00:00-05:00", "theater", 22),
    _ev(12, "Wine Flight + Vinyl Night", "Cork & Groove", "2026-07-24T20:30:00-05:00", "food-drink", 18),
    # --- free tonight ----------------------------------------------------------
    _ev(13, "Open-Air Comedy Hour", "Lawn at Mercado Park", "2026-07-24T20:00:00-05:00", "comedy", 0),
    _ev(14, "First Look Fridays: Gallery Crawl", "Eastside Art Walk", "2026-07-24T18:00:00-05:00", "visual-arts", 0),
    _ev(15, "Neighborhood Night Market", "Mercado Park", "2026-07-24T18:30:00-05:00", "community", 0),
    _ev(29, "Porch Songs: Open Stage", "The Front Steps", "2026-07-24T21:00:00-05:00", "live-music", 0),
    # --- weekend spread --------------------------------------------------------
    _ev(16, "Riverlight Festival: Day One", "Butler Shores Field", "2026-07-25T15:00:00-05:00", "festivals", 35),
    _ev(17, "Saturday Symphony Under the Stars", "Hillside Amphitheater", "2026-07-25T20:00:00-05:00", "performing-arts", 28),
    _ev(18, "Sunday Blues Brunch", "The Velvet Note", "2026-07-26T11:00:00-05:00", "live-music", 0),
    _ev(19, "Improv Marathon Weekend", "The Quip Room", "2026-07-25T19:00:00-05:00", "comedy", 14),
    _ev(20, "Night Bazaar: Makers After Dark", "Warehouse Nine", "2026-07-25T19:00:00-05:00", "nightlife", 8),
    _ev(21, "Shakespeare in the Park: Twelfth Night", "Zilker Hillside", "2026-07-26T19:30:00-05:00", "theater", 0),
    _ev(22, "Taco Trail Food Fest", "South Congress Lot", "2026-07-26T12:00:00-05:00", "food-drink", 10),
    # --- family day (today, daytime) -------------------------------------------
    _ev(23, "Dino Dig Pop-Up", "Discovery Lawn", "2026-07-24T16:30:00-05:00", "family", 0),
    _ev(24, "Family Puppet Matinee", "The Little Curtain", "2026-07-24T17:00:00-05:00", "family", 8),
    _ev(25, "Junior Ranger Creek Walk", "Barton Greenbelt Trailhead", "2026-07-24T17:30:00-05:00", "place-based", 0),
    _ev(26, "Storytime Under the Oaks", "Central Library Plaza", "2026-07-24T16:15:00-05:00", "library", 0),
    _ev(27, "Sunset Kite Hour", "Auditorium Shores", "2026-07-24T19:00:00-05:00", "family", 0),
    # --- deliberately NOT featurable: already started at the reference moment --
    _ev(28, "Lunchtime Jazz Trio", "Corner Stage Cafe", "2026-07-24T12:00:00-05:00", "live-music", 0),
]
