"""Ticket A wrap: plan() drops date/place holds. Yearless house dates get a year."""


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


try:
    _wrap_plan()
except Exception:
    pass
try:
    _wrap_house_when()
except Exception:
    pass
