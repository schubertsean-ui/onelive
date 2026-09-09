# Claude lock — read before any edit

Work only on a pull request. Never treat an issue as a PR.
Issue #278 is the ticket. PR #279 is the branch you edit.
@claude on an issue 404s. @claude on the PR edits the branch.

The Plan is docs/1Live_Platform_Plan.md on master. If anything disagrees, follow the Plan.

## This PR (#279) — three edits

1. tools/desk_ingest.py — after plan() returns, call apply_to_writes from worker.locale_pack.ticket_a_apply.
2. worker/locale_pack/desk_read.py — in _house_when delete `del as_of`. Call complete_house_year. Year never returns None for a parsed month+day. File stays over 10KB.
3. worker/locale_pack/desk_publish.py — write_for hold_reason cannot be missing date or place. File stays over 10KB.

## Allowed files
- tools/desk_ingest.py
- worker/locale_pack/desk_publish.py
- worker/locale_pack/desk_read.py
- worker/locale_pack/existence.py
- worker/locale_pack/house_year.py
- worker/locale_pack/ticket_a_apply.py
- tests for those files
- tickets/TICKET-A-POPULATE.md

## Forbidden
- Stub, PLACEHOLDER, see-file, delete desk_read.py
- Merge or reopen #273
- ingest.yml, law files, card rooms, warehouse, ceremony
- Invent T17:00, events, dates, or places
- A second ticket or a second PR

Done = this PR green with the 54KB reader still present. Then desk-ingest write=true doors=all. Then 1live.co Showing N of M moves.
