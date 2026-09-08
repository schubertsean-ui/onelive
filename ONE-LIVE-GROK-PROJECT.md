# 1Live — Grok Project pack

Ratified: 2026-09-08. Status: in force for Grok chats.
The long founder↔agent thread is **not** canon. This file plus the law files are.

**Highest priority:** real activities displaying on [1live.co](https://1live.co).
A PR, a table, a board, or a status update is not done.

---

## Already on GitHub (do not rewrite)

| File | Wins on |
|---|---|
| [ONE-LIVE-COVERAGE-LAW.md](ONE-LIVE-COVERAGE-LAW.md) | catalog scope |
| [ONE-LIVE-OPERATING-LAW.md](ONE-LIVE-OPERATING-LAW.md) | how you work |
| [ONE-LIVE-VISION.md](ONE-LIVE-VISION.md) | what 1Live is |
| [ONE-LIVE-TRUST.md](ONE-LIVE-TRUST.md) | existence vs field vs mutation |
| [ONE-LIVE-ENTITY-SPLIT-LAW.md](ONE-LIVE-ENTITY-SPLIT-LAW.md) | Happening / Place / Actor / Door |
| [ONE-LIVE-LOCALE-LAUNCH.md](ONE-LIVE-LOCALE-LAUNCH.md) | locale is a query |
| [ONE-LIVE-CONDUCTOR.md](ONE-LIVE-CONDUCTOR.md) | impediments are work |
| [CLAUDE.md](CLAUDE.md) | charter; **ceremony is OFF** |

Repo: https://github.com/schubertsean-ui/onelive  
Live: https://1live.co · Tonight: https://1live.co/tonight  
Default branch: `master`

---

## Do not import from the long thread

Leave these in the old chat. They are not instructions.

- Claude wander logs, evaluator seat politics, Kaizen/ledger/session-arc fights
- Anthropic billing / spend-cap screenshots
- GitHub Project boards and scoreboard issues (closed: #268)
- “We are walking / publishing” status narration
- Planomato clones, design-system rebuilds, new vendors
- Session 0–4 playbook as a queue (outdated)

---

## Standing rules for every Grok chat in this project

One chat = one ticket = one PR. If it is not in the Must-do, do not do it.
Print `In scope` / `Refused` before each commit. Revert unnamed files.
Ask founder only for: money, legal, credentials, production writes, class D, smoke run, **merge**.
Never merge unless founder pastes `merge`. Pending evaluator is a stop.
Do not invent dates, places, or events. Do not drop legally seen rows.
Do not bypass login / paywall / bot protection. No pay-to-rank.
Do not tell a venue we have their calendar unless they claimed or partnered.
Do not use a search snippet as a listing.
403/404 is *we* failed, not “this place has no events.”
Done = a person opens 1live.co and sees the activity.

---

## Current hole (update after every production write)

As of 2026-09-08, **production is still the last master write**:

- Chronicle: **131 published** vs ~**2,454** on their 62-page calendar (we stopped at page 40; parser skipped printed date/venue).
- Ticketmaster licensed: **1,267** in DB, **36** on /tonight (21-day window).
- Patch that takes printed date/venue and walks to the last page: **PR #267** — open, not on master, not on 1live.co.

Nothing from #267 is live until: squash-merge to `master` → Actions `desk-ingest.yml` `write=true` `doors=all` finishes → 1live.co count moves.

---

## First ticket (paste into a new Grok chat inside this project)

```
Operating Law in force. Coverage Law on scope. Ceremony off. One Must-do. Then stop.

Repo: https://github.com/schubertsean-ui/onelive
Live: https://1live.co
I am a non-coder. Numbered clicks if I must do something.

Highest priority: real activities displaying on 1live.co.

Must do:
1. Read PR #267. If evaluator is green, wait for my word “merge”. If red on a real trust defect (invented date, dropped row, wall bypass, venue-link-as-event-URL), fix THAT only, push, wait for green.
2. After I paste “merge”: squash-merge #267 to master.
3. Dispatch desk-ingest.yml on master: write=true, doors=all. Watch it finish.
4. Table only: source | pages walked | stopped_because | read | published | held | why-held
   Then open https://1live.co/tonight and report the live count vs before.
5. If published did not move: one paragraph, file/function/error. Stop.

Must not: boards, scorecards, STATE novels, new importer, login bypass, inventing dates, claiming we published before the write finishes, merging without “merge”.

Print In scope / Refused. Then stop.
```
