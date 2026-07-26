# Decision — a GitHub-native dead-man watchdog, replacing the healthchecks.io-only requirement (founder, 2026-07-26)

**Status:** RATIFIED by the founder. This amends `CLAUDE.md`'s Sentinel clause,
which previously named healthchecks.io as the only accepted dead-man mechanism.
A charter amendment is founder-only; this one was asked for and granted explicitly.

## The directive (verbatim)

> **"build the watchdog"**

Answering ask 1 option 3 in `docs/V1.md`, which had been offered as: *a scheduled
workflow that asks GitHub's own API when `import_licensed` last succeeded and fails
loudly if it is too old — no account and no secret, because the automatic
`GITHUB_TOKEN` is enough.*

## Why the founder was offered this at all

The standing directive of the same day: *"I want to do as little manual work as
possible."* Ask 1 originally required creating a healthchecks.io account and adding
a repository secret — a third-party signup. The watchdog reduces that to one word.
Under `CLAUDE.md` prime directive 6, *an option needing zero founder action beats a
better option needing one*, and *an ask you can delete is worth more than an ask you
can polish.* This deletes most of ask 1.

## What changed

The charter's requirement is now **the alarm, not the vendor.** Two mechanisms are
accepted: a healthchecks.io ping (independent of GitHub, stronger) or the
GitHub-native watchdog (zero setup). **"No scheduled loop ships without both
[Sentry and a dead-man alarm]" is untouched** — nothing was loosened. A job watched
by neither mechanism is still forbidden.

## How the alarm reaches a human

`tools/watchdog_check.py` asks the Actions API when each watched workflow last
completed *successfully* and exits non-zero if that is longer ago than the
workflow's cadence plus grace. A non-zero exit fails the scheduled run, and GitHub
emails the repository owner when a scheduled workflow fails. That email is the ping.

## The weakness the founder accepted, stated because hiding it would defeat the purpose

1. **It shares a failure domain with what it watches.** The watchdog runs inside
   GitHub Actions. On 2026-07-26 Actions stopped executing in this repo entirely
   (R-060); the watchdog would have been down alongside the jobs it watches.
   healthchecks.io does not share that failure mode — that is the entire point of an
   external dead-man switch.
2. **GitHub disables scheduled workflows in repositories inactive for 60 days.** A
   quiet period silently disarms it.
3. **Alarm delivery is an email in the same inbox as every other CI notification**,
   rather than a purpose-built escalation.

This was a deliberate trade of alarm independence for zero founder setup, made by
the founder rather than assumed by the agent. Upgrading to mechanism 1 later costs
the same two minutes it always did and requires no code change — the charter now
accepts both.

## Design choices worth keeping

- **Three explicit tables, no silent omissions.** `WATCHED` (must be scheduled and
  fresh; stale is an alarm), `EXPECTED_SOON` (should be scheduled, is not yet, each
  citing its OPEN `docs/RECORD.md` row — reported as PENDING rather than alarmed on,
  because re-screaming a registered gap every six hours is noise that teaches people
  to ignore the alarm), and `EXCLUDED` (with a substantive reason each). A test
  asserts every scheduled workflow appears in one of the three.
- **`ingest.yml` is excluded on purpose:** AI extraction is capped off at the
  provider, so every run fails for a known reason. Alarming every 20 minutes on that
  would be pure noise. The trigger to include it is the cap being raised.
- **It does not pretend to watch itself.** `watchdog.yml` is in `EXCLUDED` with the
  reason spelled out: if it is not running it cannot report that it is not running.
- **An unanswerable question is exit 2, never a pass.** A 403 from the API — which
  is what happens without a token — is a tool error, not "fresh".
- **The alarm was proven able to fire** before being accepted: stale, never-run and
  unscheduled each turn it red, asserted in `tests/test_watchdog_check.py`.

## What this does NOT do

It does not schedule `import_licensed.yml`. That is a separate action — it puts real
writes to the production database on a timer — and it is the remaining half of ask 1.
The watchdog removes the *blocker* (the charter's dead-man requirement can now be met
with no founder setup); scheduling the feed is one word away and tracked as R-055.

---

**Codified by:** `tools/watchdog_check.py` + `.github/workflows/watchdog.yml` +
`tests/test_watchdog_check.py` (18 tests, alarm proven able to fire), and the
amended Sentinel clause in `CLAUDE.md`.
