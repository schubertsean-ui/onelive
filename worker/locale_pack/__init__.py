"""Ticket A: wrap plan() after the package is loadable."""


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


try:
    _wrap_plan()
except Exception:
    pass
