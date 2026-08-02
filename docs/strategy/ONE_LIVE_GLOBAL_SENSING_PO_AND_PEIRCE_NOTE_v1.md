# Global sensing po battery + Peirce semiotics applicability — research note v1 (PROPOSAL)

Greppable summary: founder-directed research note (2026-07-14, Session
Contract #6). Part A: full chartered po battery (seed 20260715, random word
"anchor") against the scale challenge — "share all the entertainment
happening all the time: hundreds of thousands of entertainment/culture
sites and feeds globally, starting from the central Texas counties" — with
12 harvested CANDIDATE ideas. Part B: analysis of whether Peirce's triadic
semiotics can analyze po output + six thinking hats; verdict: useful in two
specific places (evidence typology, inquiry-cycle framing), decorative
elsewhere. STATUS: PROPOSAL — nothing here is canon, memory, candidate
data, or user-facing copy except by surviving the normal gates (charter
Thinking-tools rule 1). The ratified plan of record for sensing remains
`docs/strategy/ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md`.

---

## Part A — the po battery run

Target statement: *"1Live shares with users all the entertainment
happening all the time by accessing hundreds of thousands of entertainment
and culture websites and feeds around the globe, starting small with the
central Texas counties."*

Generator: `python tools/po_battery.py --seed 20260715 "<statement>"` —
all operators P1–P8.6, ≥2 movement techniques per provocation (transcript
condensed here to the provocations that yielded harvestable movement;
dead-end provocations are listed at the end for completeness).

### Step 0 — assumptions the statement takes for granted

A1 coverage requires US accessing sources (pull) · A2 sources are websites
and feeds · A3 hundreds of thousands of sources must each be handled ·
A4 1Live is the accessor (centralized crawl) · A5 "all the time" =
continuous polling · A6 geographic expansion is linear from Texas ·
A7 users are recipients, not sensors · A8 sharing = a feed we assemble ·
A9 events are announced in advance on the web · A10 more sources = more
coverage = more value · A11 the bottleneck is access/extraction cost.

### Provocations → movement → harvest (traceable)

**P1 escape — "Po: we never access any website."** Principle: information
comes TO us. The crawl exists to bootstrap the audience that makes the
crawl progressively unnecessary: entities that want reach will self-report
through the verified first-party channels the sensor architecture already
ratifies. → **H1**.

**P1 escape — "Po: there are only 12 sources in the world."** Simulated
straight, this is nearly true: a small head of aggregating platforms +
standards (ICS/RSS, ticketing and booking platforms, city open-data
portals) covers a large fraction of formal events. Two harvests: measure
the coverage curve instead of guessing (**H2**), and integrate
license-clean aggregators-of-venues before scraping individual sites
(**H3** — distinct from scraped aggregators, which stay
corroboration-only per the channel playbook; ToS/licensing review remains
founder-crucial).

**P1 escape — "Po: we don't start small; we launch everywhere at once."**
Difference: nothing county-specific may exist in code. The Texas build IS
the global build if every component is locale-parameterized config →
prove it mechanically (**H4**).

**P2 reversal — "Po: users share the entertainment with 1Live."**
User-submitted factual event sightings (incl. photographed street posters)
enter as ordinary third-party raw fetches through the same
extract→gate flow. Trust screen: never the fast lane; injection rule
applies; kept fully separate from Tastemaker opinion posts (separate trust
category, untouched). → **H9**.

**P2 opposite — "Po: we share nothing; users find everything."** The
product flips from feed to agent at the long tail: pre-crawl the hot home
markets, fetch-on-demand for cold/rare queries with honest freshness
display. → **H6**.

**P3 exaggeration up — "Po: billions of sources."** No hand-maintained
registry survives; sources must be discovered, yield-ranked, auto-demoted,
self-healed. → **H7** (with P8.1/P8.2 below).

**P3 exaggeration down — "Po: one event per year."** Every event is
precious — which is literally true in sparse rural counties. Low-density
presentation + acquisition mode as a differentiator incumbents ignore.
→ **H12**.

**P3 exaggeration (frequency up) — "Po: an event every second
everywhere."** The user-facing bar was never coverage; it is the right
five tonight. Coverage without relevance is noise — keeps the sensing
program subordinate to the product bar (no harvest; a priority check).

**P4 distortion — "Po: we publish the event before it is announced."**
Taken straight this collides with the trust invariants (a prediction can
never be `confirmed`). Movement extracts the safe kernel: recurrence
detection may direct SENSING (poll when announcement windows are
expected), never publishing. → **H10** (trust screen explicit).

**P4 distortion — "Po: users tell us where they'll be, then we find the
events."** Zero-result queries are a free, demand-weighted coverage-gap
detector that should drive source acquisition. → **H5**.

**P5 wishful — "Po: every event announces itself the moment it is
conceived."** The realizable fraction: integrate with the tools venues
already use (booking/calendar/CMS platforms) so one integration = N
venues; long-term, publish a trivially easy "announce once" path (folds
into H1/H3).

**P6 absurd — "Po: the venue's walls report their own posters."** The
poster IS a channel: a QR/short-link kit promoters put in poster footers
makes every flyer an inbound registration; user photos of posters are the
degraded-mode version (folds into H9).

**P7 random entry "anchor"** (properties: anchor tenant, news anchor,
anchor text, chain, buried, dropped/raised): anchor-tenant → each county
bootstrap starts by signing 3–5 anchor institutions whose verified
first-party feeds seed the graph and pull smaller actors in (**H8**);
anchor-text → mine curated link pages ("best of Austin") as
source-discovery + pre-classification input for the scout swarm
(**H11**); buried-anchor → some scenes (story-only, Discord-only) are
structurally invisible to crawling — honest per-market coverage
limitation, strengthens H9.

**P8 combos (operator applied to the anchor associations):**
P8.1 escape (an anchor that doesn't hold) → source drift: feeds die and
move; liveness detection + automatic re-discovery = self-healing registry
(→ H7). P8.2 reversal (the ship holds the anchor) → attribute each
verified event back to the source that surfaced it: yield attribution
prices every source (→ H7). P8.3 exaggeration (immovable anchor) →
periodic portfolio review so the registry never fossilizes (→ H7).
P8.4 distortion (raise before dropping) → probe sources BEFORE admission —
`tools/real_source_probe.py` already exists; validates current practice.
P8.5 wishful (one anchor for every ship) → the canonical event schema is
that anchor; every channel adapter converges to it — validates current
architecture. P8.6 absurd (anchors sail themselves) → autonomous scouts —
already ratified, gated + capped.

Dead ends (run, no harvest): P6 "the feed reads the user" (only creepy
readings; the private-preference version is already the Emotion spec's
lane); P7 news-anchor (a human curation layer is Tastemaker territory —
separation rule, parked).

### The harvest — 12 candidates (none are commitments)

| # | Candidate | From | Trust screen |
|---|---|---|---|
| H1 | Two-phase strategy stated explicitly: crawl bootstraps the audience; verified self-report scales it — "the crawl builds the audience that makes the crawl obsolete" | P1, P5 | uses ratified first-party channels only |
| H2 | Coverage denominator: one ground-truth census week per county → coverage % per source class; makes "all the entertainment" falsifiable and prices marginal sources | P1, P3↓ | measurement only |
| H3 | Aggregators-of-venues first: license-clean structured APIs/standards before per-site scraping; one integration = thousands of venues | P1, P5 | ToS/licensing = founder-crucial (legal), per channel playbook |
| H4 | Second-county drill: county #2 must stand up with zero code changes — config-not-code as an acceptance test | P1 | none needed |
| H5 | Demand-driven sensing: zero-result queries feed the source-acquisition queue | P4 | anonymous/aggregate only |
| H6 | Two-tier sensing: pre-crawl hot markets; query-time fetch for the cold tail with honest freshness display | P2 | freshness shown, never faked |
| H7 | Source-portfolio economics: per-source cost-per-verified-event, yield attribution, auto-demotion, drift self-healing, periodic review | P3↑, P8.1–P8.3 | §14.2 alignment |
| H8 | Anchor-institution bootstrap: sign 3–5 anchor venues/institutions per county first; verified feeds seed the graph | P7 | first-party rule as ratified |
| H9 | Community sighting channel: user-submitted factual sightings + poster photos + promoter QR kit enter as third-party raw fetches through the normal gate | P2, P6, P7 | never fast-lane; injection rule; hard-separated from Tastemaker opinion |
| H10 | Recurrence detection as a polling optimizer ONLY — predicted events are never published, never enter candidate data as assertions | P4 | explicit: prediction directs sensing, not publishing |
| H11 | Link-graph discovery: mine curated "best of" pages / anchor text to find and pre-classify sources for the scout swarm | P7 | discovery only, corroboration rules unchanged |
| H12 | Sparse-market mode: digest-style presentation + acquisition strategy for low-density counties as differentiation | P3↓ | none needed |

Disposition: H1–H12 are design-time inputs for the queued Step-7+ items in
`ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md` (watchers, push channels,
scout swarm) and TODOS carries the triage pointer. Convergence happens
through the normal gates (friction → evaluator → trust → cost) at build
time. H2 and H5 are cheap enough to consider early; H3's licensing screen
is founder-crucial before any aggregator API is used at scale.

---

## Part B — do Peirce's triadic models and semiotics help?

Founder ask: can C.S. Peirce's triadic sign model + semiotics analyze the
de Bono po ideas and the six thinking hats? ("see Proc and other
projects" — no project named "Proc" was findable; nearest real referents
are the Peirce Edition Project (IUPUI, his collected writings) and the
computational-semiotics literature applying Peirce to AI. One-line
correction welcome if a specific project was meant.)

### B1. The triadic sign, mapped to our pipeline (genuinely useful)

Peirce: a sign stands for an OBJECT and produces an INTERPRETANT (the
understanding), which is itself a sign producing further interpretants —
semiosis is a chain. Mapped: the real-world event is the object; every
web announcement/post/feed item is a sign of it; each extraction is an
interpretant; corroboration is the interpretant chain converging. Our
4-state confidence model is then a measure of interpretant stabilization,
and **disputed shown-never-hidden is Peircean fallibilism implemented**:
inquiry stays open, conflicting interpretants stay visible, nothing is
prematurely collapsed. This adds no new machinery — it shows the existing
trust model has a 150-year-old philosophical spine.

### B2. Icon / index / symbol → an evidence typology (the real dividend)

Peirce's second trichotomy classifies signs by HOW they connect to their
object: **icon** (resembles it — a poster image), **index** (existentially
/ causally connected — smoke to fire), **symbol** (connected by
convention — words). Mapped to our evidence classes:

- A DKIM/DMARC-validated message from the venue's own domain, or a post
  from its authorized in-product account, is INDEXICAL — existentially
  connected to the entity. This is precisely why the ratified first-party
  rule can admit it at `confirmed`: the connection is causal, not
  conventional.
- Third-party text descriptions are SYMBOLIC — conventional signs that
  earn trust only through corroboration (our unverified→likely climb).
- Poster photos / flyers are ICONIC + weakly indexical (a physical
  artifact existed somewhere) — right to treat as raw material for
  extraction, never as verification (H9's screen).

Recommendation: adopt icon/index/symbol as VOCABULARY in the evidence
taxonomy docs when Step 7 builds the watcher/evidence schema — it gives
reviewers a crisp test ("is this evidence indexical or merely symbolic?")
for gate arguments. Adopt the words, not a formalism.

### B3. Abduction — why po works, in Peirce's terms (useful framing)

Peirce's three inferences: **abduction** (form a new explanatory
hypothesis — he held it is the only operation that introduces any new
idea), **deduction** (derive consequences), **induction** (test them).
De Bono's po + movement is engineered abduction: the provocation forces a
jump out of the current hypothesis space; movement techniques extract the
candidate. Our loop then already completes Peirce's full inquiry cycle:
po battery = abduction → friction attack = deduction (what would break) →
validate/eval-harness/golden set = induction. The charter's rule that
"provocations are stimuli, never facts" is exactly Peirce's discipline
that abduction alone proves nothing — it only proposes. Adopt as a cited
"why it works" paragraph in `docs/skills/po_provocation.md` at its next
touch; no behavior change.

### B4. Six thinking hats (honest verdict: decorative)

The hats can be loosely draped over Peirce's categories (green/red ≈
Firstness-possibility/quality; white/black ≈ Secondness-fact/resistance;
blue/yellow ≈ Thirdness-mediation/law), and our review personas already
implement the hats' real content — parallel single-lens passes over the
same object. The mapping is intellectually pleasing and operationally
empty: it would change nothing about how a persona reviews a diff.
Verdict: do not build anything on it. (We also do not formally use the
hats today; the persona system is our equivalent and is already stronger
because each persona owns docs and a risk area.)

### B5. What NOT to adopt

No semiotic formalism layer, no ontology dependency, no new tooling.
The computational-semiotics literature (e.g. Peircean text-generation and
symbol-grounding work) is research-grade, not production-grade; adopting
it as machinery would violate least-costly-method-first for zero gate
value. Peirce's value here is a sharper vocabulary and a validation that
the trust architecture's instincts (fallibilism, indexical grounding,
corroboration as semiosis) are old, load-bearing ideas.

## Recommendations (all PROPOSAL)

1. Fold H1–H12 into the Step-7+ design work as inputs (TODOS pointer).
2. H2 (coverage denominator) and H5 (zero-result queue) are candidates
   for early, cheap builds — friction-attack them at Step 7 design time.
3. Adopt icon/index/symbol vocabulary in the evidence-schema docs at
   Step 7; add the abduction paragraph to the po skill doc at next touch.
4. Nothing else from Part B becomes machinery.
