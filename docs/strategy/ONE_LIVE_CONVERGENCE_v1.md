# 1LIVE — Data Convergence Model v1

**Status: PROPOSAL** (pending founder ratification, gap-by-gap — see §11).
Date: 2026-07-22. Author: generator session, at founder direction.
Companion documents: `ONE_LIVE_CONVERGENCE_PO_NOTES_v1.md` (the po-battery
harvest H1–H11 that seeded this design), `ONE_LIVE_SOCIAL_COMPOSITE_v1.md`
(the dossier layer that feeds it), `ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md`
(PROPOSAL — the cultural-analytics consumer, §8 here).

## 0. The founder's brief (verbatim anchor)

> "I'm envisioning a data convergence model where we have data that is
> tagged or somehow otherwise identified and categorized — one data point
> may correctly land in more than one category so we need to be nimble and
> account for and integrate logic for ambiguity — and then we have a
> multipart and potentially multiparty agent swarm evaluate and assess the
> various data and create assessments with rationale. Again ambiguity and
> imperfect knowledge should be a key element of the functionality. Then
> those assessments are perhaps run through some analog of Monte Carlo
> (research what these options might be) for accuracy and potential impact
> if wrong 100% or wrong lesser percentages. And then there needs to be
> some kind of adjudicator but not a once and done, it needs to be run
> against some factor(s) like time (of event) and other 'high confidence'
> data sources that may arrive or become visible after initial assessments.
> This may be especially useful for future events in addition to 'today' or
> 'this week' events. And this also should help feed our cultural focus and
> heartbeat analytics."

Every element of that brief has a named home below: tagging with ambiguity
(§2), the swarm with rationale (§4), the Monte Carlo analog with
impact-if-wrong (§5), the continuous adjudicator indexed on event time and
late-arriving high-confidence sources (§6), and the cultural heartbeat
(§8). The research grounding is a dedicated framework survey (uncertainty
representation, Monte Carlo variants, judge aggregation, calibration,
decision theory, temporal belief revision) whose citations appear inline;
§9 lists what the research says NOT to use, with reasons.

## 1. Plain-language overview

Today the pipeline answers "is this event real?" with counting: how many
independent sources agree. That got us to launch, but it treats every
source as equally trustworthy, every disagreement as equally serious, and
every claim as settled once gated. The convergence model replaces counting
with **measured belief**: every field of every claim carries an explicit
three-part state — how much we believe it, how much we disbelieve it, and
how much we simply don't know — and that state moves only when evidence
arrives, always with a written rationale, always leaving an audit trail.
The same machinery tells us *what the mistake would cost* if we're wrong,
*which single fetch would teach us the most*, and — because events resolve
(they happen or they don't) — *how good every source and every assessor
actually is*, measured against reality, forever.

Nothing in this proposal touches the trust invariants: the AI still never
publishes; the gate still custodies promotion; disputed is still shown,
never hidden. The convergence model is a smarter brain BEHIND the same
gate, and it enters the product path only through the ratification steps
in §11.

## 2. The data model: tags, ambiguity, and two kinds of "unsure"

**Multi-category membership is the default, not an edge case.** A show can
be genuinely jazz AND comedy; a venue is a bar AND a listening room. Tags
are therefore per-tag probabilities (multi-label), never a forced single
choice.

**Two different kinds of "unsure," kept apart mechanically** (the research
survey's central warning on fuzzy approaches: conflating them corrupts
both):

- **Vagueness** — the thing itself is a hybrid ("0.7 live-music, 0.4
  comedy" describes a comedy-jazz night accurately). This is a property of
  the event; it never decays and no amount of extra sources removes it.
- **Epistemic uncertainty** — WE don't know ("sources conflict on whether
  it's comedy at all"). This is a property of our knowledge; it shrinks as
  corroboration arrives and grows with staleness.

Each is stored on its own axis. The display layer may render vagueness
("genre-bending night"); only epistemic uncertainty drives confidence
states.

**Ambiguity is a measured product, not a nuisance** (po harvest H2):
category-membership entropy and assessor disagreement are first-class
stored values. "The scene splits on what this show is" is cultural signal
(§8), and a spike in tag entropy across a neighborhood is a finding, not
noise.

## 3. The belief substrate: Subjective Logic

The framework survey compared Dempster–Shafer evidence theory, Bayesian
networks, fuzzy/possibility theory, credal sets, and Subjective Logic
(Jøsang) as the uncertainty representation. **Subjective Logic (SL) is the
recommendation** — it was built for exactly this job (trust and reputation
fusion across unreliable sources) and the alternatives each fail a 1Live
requirement (§9).

**What it is.** Every field of every claim holds an *opinion*: belief `b`,
disbelief `d`, uncertainty `u` (with `b+d+u=1`), plus a base rate `a`
(the prior — what we'd expect knowing nothing but the category/venue).
Each opinion is mathematically identical to a Beta/Dirichlet distribution,
which means it is simultaneously:

- an **evidence ledger** — "3 confirming sources, 1 denying, prior weight
  2" reads directly out of the numbers, auditable per field;
- a **probability distribution** we can sample from (this is what makes
  the Monte Carlo pass in §5 nearly free);
- a **fusion input** — SL ships closed-form operators for combining
  opinions: *cumulative* fusion for independent sources, *averaging*
  fusion for sources suspected of copying each other (two aggregators
  syndicating one feed must not count twice), *trust discounting* to
  weaken an opinion by how reliable its source has proven, and *evidence
  aging* so stale confirmations fade.

**The 4-state model falls out by thresholding** — no redesign of the
ratified confidence states, they become measured instead of counted:

| state | opinion signature | plain reading |
|---|---|---|
| `unverified` | high `u` | nobody really knows yet |
| `likely` | moderate `b`, moderate `u` | leaning true, thin evidence |
| `confirmed` | high `b`, low `u` | strong corroborated belief |
| `disputed` | high `b` AND high `d` | sources actively conflict |

Note what this fixes: today `disputed` and `unverified` can look similar
("not confirmed"). Under SL they are *structurally different states* —
conflict (b and d both high, u low) versus ignorance (u high) — which is
exactly the distinction the disputed-shown-never-hidden invariant needs
the data model to respect.

**Implementation posture:** the operators are simple closed forms; the
survey found existing Python SL libraries thin and of unverified
maintenance. We write our own (~300 lines plus tests). Given gate-custody
rules, owning the arithmetic that feeds trust decisions is preferable to a
third-party dependency regardless.

Key references: Jøsang, *Subjective Logic* (FUSION 2022 tutorial,
mn.uio.no/ifi/personer/vit/josang/sl/subjective-logic-fusion-2022.pdf);
multi-source fusion operators, arXiv:1805.01388. The whole design is an
instance of the truth-discovery / multi-source fusion literature
(TruthFinder, Yin et al., KDD 2007; Google's data-fusion survey) — the
iterate-source-reliability-and-claim-truth loop is well-trodden ground,
not novel risk.

## 4. The swarm: independent assessors with rationale

The "multipart and potentially multiparty agent swarm" is a **panel of 3–5
independent one-shot judges** per convocation, and the load-bearing word
is *independent*:

- **Diversity on real axes, never resampling.** Judges differ by model
  family (the charter already mandates non-Claude lenses), by evidence
  slice (one judge sees only the venue's own site, another only the
  ticketing feed, another only the social dossier — asymmetric information
  measurably improves panel output), and by rubric. Re-asking one model
  five times is forbidden: correlated samples masquerading as an ensemble.
  The empirical anchor: a 2026 study measured a nine-LLM-judge panel at
  roughly *two effective votes* because of correlated errors
  (arXiv:2605.29800, characterized from abstract — see §10 flags).
- **No debate, no deliberation rounds.** The multi-agent-debate literature
  (ICLR 2025 analysis) finds debate fails to consistently beat simpler
  aggregation and *injects anchoring* that destroys the independence that
  makes panels work. Judges never see each other's output; their opinions
  meet only at the mechanical fusion layer. This is the hats-registry
  independence rule (docs/hats/README.md) applied to data assessment, now
  with citable support.
- **Rationale is mandatory and preserved verbatim.** Every assessment
  states its reasoning AND (po harvest H7) **names its falsifiers** —
  "what evidence would change my mind" — in machine-readable form (e.g.
  "venue calendar removes the listing," "ticketing feed shows a different
  date"). Falsifiers are what the adjudicator subscribes to (§6); this
  mechanizes the founder's "learn what to search for next."
- **Dissents survive** (H1, extending the ratified conflict-preserving
  Blue merge): the fused position carries its minority assessments with
  their rationale. Nothing is averaged away. At most, a non-scoring
  "conflict summarizer" pass writes the human-readable disputed rationale
  — it never feeds back into the numbers.
- **Judge output → SL opinion.** A judge's stated confidence plus its own
  measured track record (§7) becomes an opinion with calibrated weight;
  a chronically overconfident judge's opinions arrive pre-discounted.

**When the swarm convenes** (H5 — priors first): a new claim does NOT
trigger a panel. It inherits base rates instantly (this venue's listings
are 96% real; this aggregator mislabels genre 20% of the time) and most
claims resolve on cheap fusion alone. The swarm convenes only when the
decision layer (§5) says the answer is both *uncertain* and *worth money*
— token spend follows decision value, per the cost-discipline charter.

## 5. The "Monte Carlo analog": scenario scoring, impact-if-wrong, and value of information

The founder asked for a Monte Carlo–style pass scoring accuracy AND
potential impact "if wrong 100% or wrong lesser percentages." The research
survey's answer: because SL opinions ARE distributions, plain Monte Carlo
scenario sampling is exact, trivial, and the right tool — the heavier
alternatives all lose (§9).

**Scenario scoring.** For each claim: sample thousands of worlds from the
field Dirichlets and per-source reliability Betas. In each world, is the
event real? Is the date right? The start time? Classify each world:
- **fully wrong** — event doesn't exist / is cancelled (user shows up to a
  dark room: trust catastrophe);
- **partially wrong** — right event, wrong start time / wrong tag / wrong
  price (annoyance, graded);
- **right.**

Output: P(fully wrong), P(partially wrong, by mode), with failure worlds
carrying their causes ("failures cluster in worlds where the aggregator
feed is stale") — a countable, showable rationale. Cost: microseconds of
NumPy per claim.

**Expected-loss decision.** Belief and action are separated. The gate
action (surface as confirmed / show as likely / hold / flag disputed) is
chosen by minimizing expected loss under an **explicit asymmetric cost
matrix**: showing a phantom event ≫ hiding a real one ≫ a 30-minute time
error, scaled by event prominence. The matrix is a versioned, founder-
ratified config file — impact lives in the loss matrix, never smuggled
into the probability. Every threshold change is a visible diff, and per
the charter any loosening is a **gate-threshold relaxation: founder-
crucial**, enforced mechanically by the matrix being a tracked file on the
trust path.

**Value of Information (VoI).** The same arithmetic answers "should we
spend on another fetch?": the expected loss reduction from one more signal
versus its cost. A claim at 0.99 belief buys nothing from a re-fetch; a
high-traffic event three weeks out at 0.8 buys a lot. VoI *rises* as event
time approaches for unresolved high-impact claims — the founder's
"verify harder as the date nears" behavior arrives as a theorem, not a
heuristic (and it is the formal version of H5's "spend follows decision
value").

## 6. The continuous adjudicator: never once-and-done

The adjudicator is a standing process per claim, indexed on **event time**,
exactly as the founder specified. Design (framework survey §6 + po harvest
H4/H7/H8/H9):

1. **Exact sequential updating, no approximations.** Each arriving
   evidence item is a closed-form SL update — deterministic, ordered,
   replayable. (The survey explicitly evaluated particle filters /
   Sequential Monte Carlo for this role and rejected them: our state
   spaces are small enough for exact updates, and stochastic approximation
   of an exactly-computable posterior is an audit liability — §9.)
2. **Staleness is evidence** (the one idea worth stealing from the
   filtering literature): between observations, a deterministic decay step
   inflates `u`. "Confirmed three months ago, silent since" drifts back
   toward `likely` as its date approaches. Silence from a previously
   chatty source near the date *raises* uncertainty.
3. **Triggers, never a uniform clock** (H4): re-adjudication fires on
   (a) new evidence arrival, (b) a **falsifier subscription** hit — the
   evidence a standing assessment named as mind-changing has appeared,
   (c) staleness crossing a threshold, and (d) a schedule that **densifies
   toward the event**: T-30d → T-7d → T-48h → T-6h. Future events months
   out get exactly the cheap-early / intense-late treatment the founder
   called out. (Closest prior art: forecasting platforms — Metaculus
   scoring and retrieval-augmented re-forecasting, Halawi et al., NeurIPS
   2024, arXiv:2402.18563 — which re-run as news arrives.)
4. **Strata, never overwrites** (H8): every adjudication run deposits a
   layer — position, rationale, dissents, inputs-hash, time-to-event.
   The strata are simultaneously the audit trail (every-stage-auditable
   invariant) and the calibration dataset (§7).
5. **No-change affirmations** (H9): quiet re-checks log "examined,
   unchanged" so it is mechanically distinguishable from "never looked."
   (The arming-evidence discipline of Step 5, applied to beliefs.)
6. **Late-arriving high-confidence sources** need no special path: a
   venue's own correction or a ticketing-API update is just evidence with
   a high trust weight — cumulative fusion moves the opinion hard, the
   strata record why, and if it *contradicts* a confirmed state the b/d
   collision routes to `disputed` (shown, never hidden) plus admin review.

## 7. The closure loop: reality grades everyone

1Live's structural advantage over most fusion problems: **our claims
resolve.** The event happens or it doesn't, at a known time. That makes
every standing belief a scored forecast and gives us free, continuous
ground truth (H6):

- **Post-event verification is cheap** — setlist echo, social echo, the
  venue's next newsletter — and closes each claim as
  happened/didn't/changed.
- **Resolution grades sources and assessors backward** (H3): every source
  and judge that opined gets Brier-scored (mean squared error of stated
  probabilities — a proper score: honesty is optimal). Per-source and
  per-judge scores ARE the trust weights the fusion layer uses — the loop
  closes, and reliability is measured, never assumed.
- **Time-weighted scoring** (Metaculus pattern): every standing belief is
  scored over how long it stood, so the system is rewarded for updating
  *early*, not just for being right at the end — the correct incentive
  for a continuous adjudicator.
- **Calibration is a standing dashboard**: "when we say 90%, are we right
  90% of the time," per source, per judge, per category — founder-digest
  material, and the input to judge-panel weighting (§4).
- **Regime change re-learns LOUDLY** (H11): when resolutions repeatedly
  surprise the priors (a venue changes CMS, an aggregator degrades),
  the affected base rates re-fit with a Kaizen ledger row — never silent
  adaptation. Source-reliability drift is handled by evidence aging, not
  by dedicated drift-detection machinery.
- **Inter-judge correlation on resolved events** is a standing Kaizen
  metric: if two "independent" judges err together, the panel has fewer
  effective votes than seats, and the diversity axes get rebalanced.

## 8. The cultural heartbeat: analytics from resolved ground

The founder's "cultural focus and heartbeat analytics" consume the
**resolved strata** — post-event verified ground truth — never raw
unresolved belief (H10):

- **Genre momentum** — verified event volume and attendance signals by
  tag, over time, per neighborhood.
- **Venue vitality** — resolution rates, cancellation rates, listing
  accuracy trends per venue.
- **Ambiguity as cultural signal** (H2) — rising tag entropy in a scene
  ("shows that defy one genre") is itself a heartbeat metric, the
  quantitative trace of scenes cross-pollinating.
- The Emotion & Vibe layer (`ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md`,
  still PROPOSAL) plugs in here when ratified: its Emotion Graph would run
  on the same resolved strata, inheriting this spec's provenance
  discipline for free.

Building analytics on resolved strata (not live beliefs) means the
heartbeat can never be polluted by an ingestion error that the closure
loop later catches — the cultural layer inherits the trust layer's
verification by construction.

## 9. Do not use (researched, with reasons)

The framework survey evaluated and **rejected** the following; recorded
here so future sessions don't re-litigate:

- **Dempster's rule of combination** (classical DS fusion): produces
  certainty in near-impossible options under high conflict (Zadeh
  pathology) — and high conflict is precisely our most important regime.
  SL keeps the good DS ideas (explicit unknown mass, conflict-as-signal)
  without the pathology. If set-valued mass is ever truly needed, PCR5/6
  redistribution rules are the fix — but SL covers the need first.
- **Particle filters / Sequential Monte Carlo**: approximation machinery
  for state spaces too big to update exactly; ours are tiny and discrete.
  Adds stochastic non-replayability and degeneracy failure modes for zero
  benefit. Exact conjugate updates + staleness decay give the same
  architecture, deterministically.
- **Kalman filtering**: linear-Gaussian continuous states — categorically
  the wrong data type for discrete claims.
- **PyMC / Stan in the runtime path**: MCMC latency (seconds-to-minutes)
  versus microsecond closed-form updates, and discrete latents are their
  weakest case. Legitimate ONLY offline, monthly: fitting hierarchical
  hyperparameters (per-category error rates, source-reliability priors)
  from resolved-event ground truth.
- **Multi-agent debate / iterative Delphi**: doesn't reliably beat simple
  aggregation and injects anchoring that erodes judge independence — the
  one property the panel design cannot lose.
- **MC-dropout-style resampling of one model**: correlated samples
  masquerading as an ensemble; consistently worse calibration than true
  diversity.
- **Bayesian truth serum / peer prediction / LMSR prediction markets**:
  incentive machinery for strategic humans without ground truth. Our
  judges aren't strategic and events resolve — proper scoring dominates.
  Revisit only if a human tastemaker-elicitation layer ever needs it.
- **Credal sets / full imprecise probability**: NP-hard inference,
  research-grade tooling, marginal gain over SL's uncertainty mass.
- **Learned mixture-of-experts judge weighting**: needs resolved-event
  volume that doesn't exist yet. Objective trigger to revisit: ≥1,000
  resolved events with per-judge scores banked. Until then: track-record
  (Brier) weighting.
- **Importance sampling / formal Sobol sensitivity**: adopt only if
  measured need appears (tail-risk on high-impact events; gate-health
  attribution beyond one-at-a-time perturbation). Plain MC and
  perturbation cover today's scale.

## 10. Research verification flags (honest limits)

- SL Python libraries: existence verified, maintenance not — hence the
  in-house-implementation posture (§3).
- "Nine judges, two effective votes" (arXiv:2605.29800) and the Delphi
  automation details were characterized from abstracts, not full-text
  reads.
- Several 2026 arXiv results are unreviewed preprints; treated as
  directional, and nothing in this design depends on any single one.

## 11. Build phases and founder decisions

Phasing (each phase shippable, tested, and SHADOW-FIRST — the existing
count-based gate3 remains the deciding gate until the founder ratifies
each coupling; the convergence engine runs alongside, logging what it
*would* have decided, until its shadow record earns promotion):

- **C1 — substrate.** In-house SL module (opinions, fusion operators,
  trust discounting, aging) + strata store + 4-state threshold mapping,
  full test coverage incl. golden fusion cases. Shadow-scores existing
  candidates; zero product-path coupling.
- **C2 — scenario + decision layer.** MC scenario scoring, expected-loss
  arithmetic, VoI computation; DRAFT cost matrix delivered to founder for
  ratification. Still shadow.
- **C3 — panel.** Judge harness on the existing model-router, diversity
  axes, falsifier-naming output schema, dissent-preserving fusion. Panel
  convocations VoI-gated from day one. Still shadow.
- **C4 — adjudicator + closure.** Trigger scheduler (densifying + falsifier
  subscriptions), staleness decay, post-event resolution jobs,
  Brier/time-weighted scoring, calibration dashboard. Now the shadow
  record accumulates measurable accuracy vs. the live gate.
- **C5 — coupling decision.** With shadow calibration in hand, the founder
  decides per §11 whether/where convergence outputs feed gate3. Heartbeat
  analytics (resolved-strata consumers) can ship independently of this
  decision.

**Founder-crucial decisions this spec queues (consolidated, no urgency —
all of C1–C4 proceeds in shadow without them):**

1. **Ratify the asymmetric cost matrix** (C2 delivers the draft with
   concrete numbers and worked examples). This is the gate's value system;
   it is founder voice, not agent judgment.
2. **Ratify any coupling of convergence outputs into gate3/promotion**
   (C5). Until then, shadow only — this is the same
   gate-coupling-is-founder-crucial rule the social-composite spec
   carries.
3. **Ratify the 4-state threshold mapping** (the b/d/u cutlines for
   unverified/likely/confirmed/disputed) at C5, since it becomes the
   user-facing meaning of those words.
4. Heartbeat analytics surfacing (what, where, to whom) — ties into the
   Emotion & Vibe spec's pending ratification.
