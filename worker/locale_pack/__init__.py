"""Ticket A: every plan() result drops date/place holds."""
from worker.locale_pack.ticket_a_apply import apply_to_writes


def _wrap_plan() -> None:
    from worker.locale_pack import desk_publish

    original = desk_publish.plan

    def plan(one, registrations):
        return apply_to_writes(original(one, registrations))

    desk_publish.plan = plan


_wrap_plan()
