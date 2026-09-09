# Claude lock — read before any edit

You work for the PM. The Plan is docs/1Live_Platform_Plan.md on master. If a comment, CLAUDE.md, or prior habit disagrees with that Plan, follow the Plan.

## Allowed this ticket
- tools/desk_ingest.py (add apply_to_writes after plan() only)
- worker/locale_pack/desk_publish.py (edit hold_reason + registration_for in place; keep file >10KB)
- worker/locale_pack/desk_read.py (_house_when only; keep file >10KB)
- worker/locale_pack/existence.py
- worker/locale_pack/house_year.py
- worker/locale_pack/ticket_a_apply.py
- tests that prove titled rows are not held and yearless month+day is not None
- tickets/TICKET-A-POPULATE.md

## Forbidden
- Replace desk_read.py or desk_publish.py with a stub, PLACEHOLDER, or see-file
- Merge or reopen #273 or any branch that deleted desk_read.py
- Edit ingest.yml, ONE-LIVE-*.md laws, CLAUDE.md ceremony, web card rooms, warehouse
- Invent T17:00, events, dates, or places
- Start a second ticket, write a new plan, or rewrite Vision
- Cancel an in-flight Ticket A job to do something else

Done = PR green with the 54KB reader still present. Then desk-ingest write=true doors=all. Then 1live.co Showing N of M moves.
