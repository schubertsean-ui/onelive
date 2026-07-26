# SPRINT_LIVE_SITE — SUPERSEDED 2026-07-26

**This plan is superseded. The live plan is [`docs/V1.md`](V1.md).**

Its content was deleted rather than updated because it was factually false: it
stated in bold *"PLAN ONLY — nothing in this file has been executed. Zero
deploys, zero migrations, zero spend so far,"* while thirteen migrations were
applied, the ingestion cron was armed, and the AI budget had been exhausted.
The original text is in git history (`git show HEAD~1:docs/SPRINT_LIVE_SITE.md`
from the 2026-07-26 audit commit).

**Why this tombstone exists instead of nothing:** `.github/workflows/ingest.yml`
cites this path in the error message it prints when an Actions secret is missing,
and `ingest.yml` is permanently inside the armed cron's runtime closure
(`tools/arming_runtime.py`) — so editing that one string would invalidate the
arming evidence binding and demand a fresh paid smoke run
(`tests/test_arming_smoke_binding.py`). Keeping a valid pointer here costs
nothing and keeps that gate honest. The next change that legitimately re-binds
the arming evidence should repoint the message at `docs/V1.md` and delete this
file. Classified HISTORICAL in `docs/INDEX.md`.
