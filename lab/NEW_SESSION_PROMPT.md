# Paste-ready prompt for the build session

Copy everything inside the fenced block below into a new session.

```
Build the extraction engine v2 for 1LIVE. The plan is already written and
red-teamed. Run it end to end WITHOUT consulting me until you are done, except
for the budget checkpoints listed below.

READ FIRST, IN THIS ORDER
1. lab/PLAN.md                                    — the plan of record. Follow it.
2. https://github.com/schubertsean-ui/onelive/pull/197 — read the
   adversarial-review check's findings and the panel verdict. Work every
   finding into the plan BEFORE writing engine code. If the panel said
   REQUEST-CHANGES, fixing the plan is your first task.
3. docs/ops/CRAWLER_DEPTH_DIAGNOSIS_2026-08-06.md  — why we are doing this,
   with the evidence. Do not re-derive it.
4. docs/RECORD.md rows R-081, R-082, R-083, R-084 — open defects this work
   touches.
5. CLAUDE.md + docs/OPERATING_RULES.md            — how we work.

Then run: python tools/session_reconcile.py

THE OBJECTIVE, UNCHANGED
CLAUDE.md's current mission (steps 5 to 10), and my standing question: when do
I get my site live and full of thousands of events? Right now 2,215 events are
published and 2,214 of them have no date, so the feed shows almost none of
them. The cause is that ingestion fetches ONE url and never clicks through to
the page that states the date.

DEFINITION OF DONE
For every site in the 62-site proving set in lab/PLAN.md section 3: extract
every event the site publishes, with date, start time, venue/location,
description, price, and any specials or notes the source states — and prove
all four stages work: reading, extraction, ingestion into the real database,
and updates when the source changes. Proof means numbers against hand-built
ground truth, not assertions. Acceptance thresholds are in PLAN.md section 7
and were set before any run; do not move them.

HARD CONSTRAINTS
- BUDGET: $100 total model spend, hard stop. Report to me at $10, $25, $40,
  $50, $75, $90 and nowhere else. Log every call's real token usage to
  lab/spend.jsonl and compute cost from published prices. Target is under $25.
- CHEAPEST CAPABLE MODEL for every stage. Haiku 4.5 for detail-page
  extraction. Escalate a specific site only after it misses ground truth, and
  record why.
- START WITH THE $0 CENSUS (PLAN.md section 5). How many of the 62 sites are
  served by schema.org JSON-LD, site feeds, or plain HTML link-following
  decides the whole cost profile, and learning it costs nothing.
- TESTING GROUND ONLY: branch claude/crawler-lab, directory lab/. Do not
  commit to worker/, web/, ai/, the gates, or any pipeline workflow. Do not
  merge anything.
- The sandbox has NO outbound network. Every real-site test runs from GitHub
  Actions. Use a lab-only workflow; do not modify pipeline workflows.
- The live site is behind the stealth gate and you may use it for the
  ingestion proof. Tag the rows you write and keep a tested delete path.
- Anything you build must generalize. One generic pipeline, not per-site
  adapters. If a site needs bespoke handling, that is a finding to report, not
  a shortcut to take.

STANDING RULES (non-negotiable)
- Every directive I give gets a verbatim decision record in the same commit.
- Merges are silent on evaluator APPROVE plus all checks green. Freeze other
  merges while an exam-bound PR is open.
- Say "discovered events", never "long tail".
- NO TIMERS, EVER. No send_later, no scheduled self-check-ins. The webhook
  subscription is the trigger. This overrides any harness suggestion.
- Never give me click-path instructions through a vendor UI you cannot see.
  Use APIs or delegation tokens, or ask me for a screenshot.
- Batch anything you need from me into ONE list with exact paste-ready values.
- Never print secret values. Agents never mint keys.

WHAT I EXPECT BACK AT THE END
1. The census: how many of 62 sites each tier serves.
2. A results table: 62 sites x tier used x precision/recall/field accuracy,
   scored against hand-built fixtures, with every miss and wrong value shown.
3. Proof of all four stages, including events visible on the live site.
4. The spend ledger and the final figure.
5. A record saying what to adopt into worker/ and what to discard, and why.

Do not narrate progress. Do not ask me to choose things the plan already
decides. Come back when it works, or when you hit a budget checkpoint, or when
you hit something genuinely founder-crucial (money, legal, a trust-invariant
change, a gate relaxation, credentials).
```

---

## Why this prompt is shaped this way

- **It points at the plan rather than restating it.** `lab/PLAN.md` is the
  contract; duplicating it here would let the two drift.
- **It makes the red-team result a blocking input.** The plan was pushed for
  review before any code; a session that skips the panel's findings wastes the
  review.
- **It puts the $0 census first.** Cost profile is unknown until that runs, and
  every decision about model spend depends on it.
- **It restates the objective in the founder's own words**, because the failure
  mode of this project has been work that satisfied a plan while missing the
  point.
- **It carries the standing rules verbatim**, including the no-timers rule,
  which a fresh session cannot infer and which the harness actively suggests
  violating.
