"""Definition-of-done check for the /tonight feed: every event must be at least
'likely' confidence and have a resolved venue.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/definition_of_done.py)
"""


def definition_of_done(tonight_events: list[dict]) -> bool:
    if not tonight_events:
        return False
    for e in tonight_events:
        if e.get("confidence") not in ("likely", "confirmed"):
            return False
        if not e.get("venue", {}).get("venue_id"):
            return False
    return True
