# ONE LIVE — The Shared, Learning Acquisition Toolkit (v1)

Status: BUILT and proven (`brain/acquisition.py`, `brain/seed_acquisition.py`,
`brain/acquisition_demo.py`, `tests/test_acquisition_toolkit.py`). This document
articulates the full operation to world-class standards, in plain language, and
marks the parts that are staged (not yet live) with `R-###` Record rows rather
than claiming them done.

Author: build agent, session 2026-07-25. Reviewer path: gate-custody-adjacent
memory tooling — through the independent evaluator like any `brain/` change.

---

## 1. The problem, in one sentence

Every time an agent goes to read a source's events, it was re-discovering *how*
to read that source — is there an ICS feed? is the page a JavaScript shell that
needs rendering? where is the real calendar (not the homepage)? — and then
throwing that knowledge away when the session ended. That is wasted work and,
worse, it means the agent never gets *better* at acquisition over time.

The toolkit fixes this by giving OneLive a **durable, shared memory of how to
acquire each source**, that every agent **reads before acquiring** and **writes
back to after acquiring**, so the common know-how *enlarges and improves* with
every run instead of resetting to zero.

## 2. Two things it remembers: recipes and techniques

**A recipe is per-source know-how** — "how to read *this* venue." It records the
real calendar URL (not the homepage), the access method (`plain_http`,
`js_render`, `ics_feed`, `jsonld`, or `api`), whether the page needs rendering,
the structured format if any, a segmentation hint (how to isolate each event on
the page), the legal posture (robots/ToS and the source's own
`explicitly_disallowed` list), running telemetry (last attempt/success, last
yield, median yield, an evolving reliability score, a cost hint), and the
provenance of who learned it and how confident we are.

**A technique is general, reusable know-how** — "how to read a *class* of page,"
not tied to any one source. Each technique has a description, the page *signals*
that should trigger it, and a running success record (`attempts`/`successes`)
accumulated **across every source it was ever used on**. The library ships
seeded with the methods we already built:

| Technique | Fires when the page signal is… | Cost |
|---|---|---|
| `respect-robots-tos-gate` | always, first, on every source | none |
| `detect-js-shell-then-render` | `js_shell` / `squarespace` / `wix` | high |
| `find-ics-on-wordpress` | `wordpress` / `the-events-calendar` | low |
| `parse-jsonld-graph-event` | `has_jsonld` / `jsonld` / `squarespace` | low |
| `parse-ics-feed` | `ics` / `ics_feed` | low |
| `parse-localist-feed` | `localist` | low |
| `segment-repeated-event-blocks` | `repeated_blocks` / `listing_page` / `multi_event` | low |

The split matters: a recipe says "for Mohawk, use the ICS feed"; a technique
says "ICS feeds succeed 72% of the time and cost almost nothing." A new source
with no recipe yet still benefits from the technique library the moment an agent
recognises its page signal.

## 3. The learning loop: read before, record after

```
recipe = toolkit.recipe_for(source_id)     # READ — don't re-discover
technique = toolkit.best_technique(signal)  # READ — pick the proven method
   ... acquire (the existing importers / fetchers do the real work) ...
toolkit.record_outcome(source_id, run_id=…, method=…, technique=…,
                       yield_count=…, success=…, cost=…, notes=…)  # WRITE
```

`record_outcome` is where the toolkit gets smarter. It updates the recipe's
`last_attempt_at` / `last_success_at`, appends the yield to a bounded history and
recomputes the **median yield**, and moves the **reliability** score with an
exponential moving average toward 1.0 on a real success and 0.0 on a failure —
the same "outcomes decay or reinforce a bounded 0..1 score" idea already used in
`worker/source_reliability.py`. It also updates the named technique's success
stats. A "success" that returned **zero events** is treated as *not* a real
success — a page that yields nothing did not truly work.

## 4. How sharing works: the brain is the persistence, disk is truth

The toolkit is **not** a new database. It is stored *through* the existing
persistent knowledge-graph brain (`brain/graph.py` + `brain/store.py`). A recipe
is a graph **Entity** (keyed by source_id) plus a **Claim** holding its state,
joined by typed edges to a **Source** and the **AgentRun** that learned it. The
whole graph serialises to an append-only JSONL file on disk.

That single design choice buys sharing for free: any agent, in any session, that
loads the brain graph sees the **same** recipes and techniques, already improved
by whoever ran before them. There is no separate sync step and no "chat memory"
that evaporates — **disk is truth** (CLAUDE.md prime directive 2). The demo
proves it end-to-end: agent A records a successful acquire, the toolkit is saved,
a **fresh** toolkit is loaded in a new object that never saw agent A, and agent B
reads the improved recipe straight off disk.

## 5. Provenance and auditability (inherited, not bolted on)

Because recipes and techniques are ordinary brain Claims, they inherit the
brain's **four write invariants** mechanically:

1. **Every state Claim cites a Source** — you cannot store a recipe with no
   provenance root; the brain raises loudly if you try.
2. On top of invariant 1, this module **binds every write to the AgentRun** that
   learned it (a `DERIVED_FROM` edge and a required `run_id`), so a recipe's
   history answers "*which run* learned this, from *what*, and *when*."
3. Every state update **supersedes** the prior Claim rather than overwriting it
   (invariant 4 — nothing is ever deleted), so a recipe carries its full,
   queryable **version history** and a bad update is reversible, not a
   catastrophe.

You can walk the graph from any recipe back to the exact acquisition
observations that shaped it. That is auditability by construction.

## 6. The legal rails: never a bypass recipe

This is physics, not policy (CLAUDE.md Prime Directive; §5 data-trust). A recipe
**can never encode a method that bypasses a login, a paywall, or robots.**
`_assert_recipe_legal` runs before any recipe is stored and **hard-rejects,
loudly**, any recipe that: uses a method outside the five policy-safe ones; sets
`robots_ok=False`; or describes an active bypass (login / paywall / credential /
captcha / evasion) in any of its *action* fields.

A crucial distinction the code gets right: a source's own
`explicitly_disallowed` list (which legitimately contains phrases like
"login_scraping") is a **guardrail we carry**, not an action we take — it is
stored on the recipe as a reminder of what *not* to do, and it is *not* scanned
as if it were our plan. So the rail rejects a genuine bypass while never
false-rejecting an honest recipe that merely *documents* the source's limits.
Opt-in / manual / benchmark channels (email-forward, claimed upload, the
search-engine benchmarks) are seeded with `automated_ok=False` so the toolkit
knows they are legitimate but must not be auto-fetched.

## 7. Cost-awareness: the cheapest technique that meets the bar

CLAUDE.md's "least costly method first" is built into ranking. Every recipe and
technique carries a `cost_hint`. `best_technique(signal)` returns the
**highest-success** applicable technique and breaks ties toward the **cheaper**
one. In practice that means an offered ICS/JSON-LD feed (cheap, authoritative)
is preferred over a plain HTML scrape, which is preferred over a headless render
(expensive) — and the render only wins when its *measured* success rate on that
page class actually justifies the cost.

## 8. The re-discovery trigger: catching a moved page

Pages move. A source that silently starts returning nothing is lost coverage.
The toolkit watches for this: two consecutive **zero-yield** acquisitions flip
the recipe's `needs_rediscovery` flag to True and lower its confidence — for
example when extraction emits the
`AI_EXTRACT_ZERO_EVENTS_SOURCE_MAY_HAVE_MOVED` signal. A flagged recipe is a
work item: an agent should re-discover the real calendar URL / method rather
than keep hammering a dead page. A later successful acquire clears the flag.

## 9. The steps the founder's list did not enumerate (world-class additions)

The founder's directive named the read/record loop, recipes, techniques, and the
re-discovery trigger. World-class agentic acquisition needs more than that to be
trustworthy and self-improving. The following were **added** beyond the
enumeration; the ones that are staged carry a Record row:

1. **Per-technique success telemetry (BUILT).** Techniques carry
   `attempts`/`successes` accumulated across sources and a Beta-smoothed
   `effective_success_rate`, so a prior rules until real evidence arrives and
   ranking is stable and deterministic from the first run.

2. **Recipe versioning / supersession (BUILT).** Every update supersedes the
   prior state Claim using the brain's own `supersede`, so a recipe's full
   history is queryable and no learning is ever silently overwritten.

3. **Evolving reliability + median yield (BUILT).** Reliability moves by EWMA
   (reinforced by successes, decayed by failures) and yield is summarised by a
   median over a bounded window — robust to a single outlier acquire.

4. **Confidence decay on failure/staleness (BUILT, partial).** Confidence drops
   on empty/failed acquires. Time-based decay purely from *staleness* (a recipe
   untouched for N days losing confidence even without a new failure) is staged —
   see R-037.

5. **The legal rail as a hard reject (BUILT).** Covered in §6.

6. **Automated-vs-manual channel awareness (BUILT).** Opt-in / manual /
   benchmark sources are marked `automated_ok=False` so the toolkit never
   auto-fetches a channel that is legitimate only by human action.

7. **Homepage-vs-real-calendar honesty (BUILT, partial).** Seed recipes flag
   `calendar_url_is_homepage=True` when the catalog only gave a homepage; finding
   the true listing URL is itself a per-source learning step. Auto-discovery of
   the real calendar URL is staged — see R-037.

8. **Conflict handling when two agents learn different recipes (STAGED, R-038).**
   Today writes are last-writer-wins via supersede on a single-writer JSONL
   snapshot; two agents concurrently learning *different* methods for one source
   would serialise, and the loser's learning is retained in history but not
   merged. A real merge/arbitration policy (prefer higher measured
   reliability; flag genuine disagreement) is staged.

9. **A human-review path for a recipe that starts failing (STAGED, R-039).**
   `needs_rediscovery` marks the recipe; wiring that flag into an ops review
   queue (so a person is actually asked to re-discover) is staged — the flag
   exists, the queue does not yet.

10. **Live-pipeline adoption (STAGED, R-040).** The toolkit is a proven,
    self-contained foundation; nothing in the live ingestion path reads or writes
    it yet. Wiring `worker/orchestrator.py` to consult `recipe_for` before a
    fetch and call `record_outcome` after is its own contract-first PR (and the
    orchestrator is owned by another agent this session).

## 10. What it deliberately does not do

- **It never publishes.** Like the rest of `brain/`, it must not import
  `worker.promote`; `tools/trust_gate.py` enforces that. Knowing *how* to read a
  source is upstream of, and walled off from, the gate that decides what reaches
  users. The toolkit informs acquisition; it has no opinion on trust,
  corroboration, or promotion.
- **It does not do the fetching itself.** The real work stays in the existing,
  policy-safe modules (`worker/importers/structured_feed.py`,
  `worker/fetch/render_fetch.py`, `worker/segment.py`). The toolkit is the memory
  that tells those modules *which* method to use and *learns from* how they did.
- **It invents nothing.** A seed recipe never fabricates a calendar path it does
  not have; it flags the homepage honestly instead.

## 11. Where the code lives

- `brain/acquisition.py` — the toolkit (`AcquisitionRecipe`,
  `AcquisitionTechnique`, `AcquisitionToolkit`, the legal rail).
- `brain/seed_acquisition.py` — idempotent seeding from
  `sources/master_sources_catalog_120.json` + the technique library.
- `brain/acquisition_demo.py` — `python -m brain.acquisition_demo`: the
  shared-learning proof (agent A learns → save → fresh load → agent B inherits),
  plus the moved-page trigger and the legal-rail rejection.
- `tests/test_acquisition_toolkit.py` — 24 proof tests.
- Record rows: R-037 … R-040 in `docs/RECORD.md` (staged items above).
