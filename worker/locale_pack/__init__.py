"""Ticket A wrap: titled rows publish. Date-only when stays a date."""


def _wrap_plan() -> None:
    from worker.locale_pack import desk_publish
    from worker.locale_pack.ticket_a_apply import apply_to_writes

    original = desk_publish.plan
    if getattr(original, "_ticket_a_wrapped", False):
        return

    def plan(*args, **kwargs):
        return apply_to_writes(original(*args, **kwargs))

    plan._ticket_a_wrapped = True
    desk_publish.plan = plan


def _wrap_house_when() -> None:
    from worker.locale_pack import desk_read
    from worker.locale_pack.ticket_a_apply import fill_house_date

    original = desk_read._house_when
    if getattr(original, "_year_wrapped", False):
        return

    def _house_when(card_text, page_html, as_of):
        got = original(card_text, page_html, as_of)
        if got:
            return got
        return fill_house_date(card_text, as_of)

    _house_when._year_wrapped = True
    desk_read._house_when = _house_when


def _wrap_date_only_clock() -> None:
    """Date-only when stays YYYY-MM-DD. Do not stamp 17:00."""
    from worker.locale_pack import desk_publish

    original = desk_publish._night_as_public_clock
    if getattr(original, "_date_only_wrapped", False):
        return

    def _night_as_public_clock(night: str) -> str:
        text = (night or "").strip()
        if len(text) >= 10 and text[4] == "-" and "T" not in text[:11]:
            return text[:10]
        return original(night)

    _night_as_public_clock._date_only_wrapped = True
    desk_publish._night_as_public_clock = _night_as_public_clock


try:
    _wrap_plan()
except Exception:
    pass
try:
    _wrap_house_when()
except Exception:
    pass
try:
    _wrap_date_only_clock()
except Exception:
    pass
