# Epiplexity — completed review v1.1 (primary source verified) — arXiv 2601.03220v2 vs the OneLive pipeline

Greppable summary: COMPLETED REVIEW, superseding the secondary-source scout
(ONE_LIVE_EPIPLEXITY_SECONDARY_SCOUT_v1.md, whose provisional status this
document resolves). R-024's trigger fired 2026-07-22: the founder supplied
the primary paper directly (PDF upload, arXiv:2601.03220v2 stamp "16 Mar
2026" on p.1), and it was read IN FULL — all 65 pages: main text pp.1–30,
references pp.30–36, appendices A–H pp.37–65, including every proof
appendix. Every load-bearing claim in the scout was checked against the
paper; the verification ledger is §6. Net result: the scout's reported
formal core is VERIFIED (including the exact statement of Theorem 13 and
the emergence-driven non-monotonicity mechanism), with enumerated
refinements (requential coding was missing; the existence theorem
guarantees only logarithmic epiplexity growth; naive time-bounded
sophistication provably collapses, which sharpens what is genuinely new).
All four applicability verdicts STAND and are now final: ADOPT the P3
`structural_yield` observability metric; ALIGNS/no-change for golden-set
curation, model routing, and the Descriptor Foundry; REJECT any
structure-derived signal on trust surfaces — now directly supported by the
paper's own scope statement that epiplexity measures the AMOUNT of
structural information "irrespective of its content."
Status: REVIEW/ANALYSIS — no proposal requiring ratification; no gate,
threshold, or pipeline change rides on this document. R-024: RESOLVED by
this document (see docs/RECORD.md).

## 1. What the paper is (verified against the primary)

"From Entropy to Epiplexity: Rethinking Information for Computationally
Bounded Intelligence." Marc Finzi*, Shikai Qiu*, Yiding Jiang, Pavel
Izmailov, J. Zico Kolter, Andrew Gordon Wilson (*equal contribution;
Carnegie Mellon + New York University). arXiv:2601.03220, v2 dated 16 Mar
2026. Code: github.com/shikaiqiu/epiplexity. Funding: NSF CAREER, NSF
CDS&E-MSS, DARPA AIQ; Google TPU Research Cloud compute.

The abstract's own framing, condensed: Shannon information and Kolmogorov
complexity "come up nearly empty-handed" on what data is worth learning
from, "in part because they assume observers with unlimited computational
capacity." The paper introduces epiplexity, "a formalization of information
capturing what computationally bounded observers can learn from data,"
splitting information into structural content (epiplexity) and
time-bounded entropy ("the random unpredictable content exemplified by
pseudorandom number generators and chaotic dynamical systems"), and
positions it as "a theoretical foundation for data selection."

The three motivating paradoxes (§1 and §5 of the paper, verbatim titles):
(1) "Information cannot be increased by deterministic processes" — yet
PRNGs, synthetic data, mathematics-from-axioms, dynamical systems, and
AlphaZero-style self-play all create learning value; (2) "Information is
independent of factorization order" — yet LLMs learn English better
left-to-right than reversed (the "arrow of time"), and cryptography is
built on functions hard in one direction; (3) "Likelihood modeling is
merely distribution matching" — yet a bounded observer of Conway's Game of
Life must learn object species and behaviors an unbounded simulator never
needs.

## 2. The formal core — VERIFIED

- **Observer model (Definition 7, "Time-bounded probabilistic model"):**
  fix a prefix-free universal Turing machine U and a non-decreasing
  time-constructible bound T. A program P is a T-time probabilistic model
  over {0,1}^n if it supports BOTH probability evaluation (Prob_P(x) within
  T(n) steps) and sampling (Sample_P(u) within T(n) steps), normalized and
  matching. P_T is the set of all such programs. This single bound covers
  the cost of using the model; the cost of FINDING it enters through the
  estimator's training-time accounting (§4 of the paper).
- **Definition 8 (Epiplexity and Time-Bounded Entropy):** for a random
  variable X on {0,1}^n, let P* = argmin over P ∈ P_T of
  {|P| + E[log 1/P(X)]} (ties to the smallest program). Then
  **S_T(X) := |P*|** (epiplexity — the model bits) and
  **H_T(X) := E[log 1/P*(X)]** (time-bounded entropy — the residual data
  bits). MDL_T(X) := S_T + H_T. Defined over random variables — for ML, X
  is the entire dataset, and epiplexity typically grows with dataset size.
- **Basic properties (verified, p.10):** S_T, H_T ≥ 0;
  H(X) ≤ S_T+H_T ≤ n+c₁; MDL is non-increasing in more time; and
  MDL_{T'}(f⁻¹(X)) ≤ MDL_T(X)+|f|+c₂ — the bounded analog of information
  non-increase, which is now ASYMMETRIC: a short fast program for f⁻¹ does
  not imply one for f. That asymmetry carries all three paradox
  resolutions.
- **Conditional versions (Definition 11):** S_T(Y|X), H_T(Y|X) over
  conditional models — this is the quantity their ECA and induction
  experiments actually measure.
- **Uniform/simple data:** uniform random variables have S_T ≤ c (the
  uniform model is a constant-size program) with H_T ≈ n; periodic
  patterns have both O(1). Structure-vs-noise separation behaves at the
  edges exactly as claimed.

## 3. Theorems — checked in main text AND appendix proofs

- **Theorem 9 (PRGs: maximal randomness, no structure):** for any PRG G
  with advantage ε(k) stretching to n bits: n−2−nε(k) < H_Poly(G(U_k)) ≤
  n+c and S_Poly(G(U_k)) ≤ c+nε(k). Proof (App. A.1/A.3, read): builds
  poly-time threshold distinguishers D_t from any candidate short model
  and applies a layer-cake argument; PRG security bounds their advantage.
  Kolmogorov calls a CSPRNG stream trivial (≈ seed length); every
  poly-bounded learner experiences it as pure noise; epiplexity sides with
  the learner. VERIFIED.
- **Theorem 10 (High-epiplexity data exists, conditionally):** assuming
  one-way functions (secure against non-uniform PPT), there exist random
  variables with S_Poly(X_n) = Ω(log n). Proof (App. A.4, read): counting
  argument over PRF keys — a union bound over all short models yields a
  hard key K* whose keyed distribution no log-size model fits. IMPORTANT
  HONESTY the scout under-weighted: the guaranteed growth is only
  LOGARITHMIC — the paper itself says this "only admits a very modest
  amount of structural information, still far from the power law scaling
  we see with some natural data," and the argument is nonconstructive. The
  gap between what the theory guarantees and what the estimator measures
  on natural data is real and acknowledged.
- **Theorem 12 (Computation creates information):**
  H_Poly(G(U_k)) − H_Poly(U_k) > n−k−nε(k)−c — a deterministic function
  dramatically increasing time-bounded information. Practical corollary
  stated by the authors for synthetic data: "we should make sure the
  functions we use do not have simple and efficiently computable
  inverses." VERIFIED.
- **Theorem 13 (Factorization asymmetry) — the scout's weakest-sourced
  claim, now VERIFIED VERBATIM:** for a one-way permutation f, X = U_n,
  Y = f(X): H_Poly(X|Y) + H_Poly(Y) > H_Poly(Y|X) + H_Poly(X) + ω(log n).
  Time-bounded entropy violates the classical symmetry of information.
  Appendix Theorem 25 is the formal version (for every constant c there
  exists N such that the gap exceeds c·log n for all n ≥ N); the proof
  (App. A.5, read) is a clean Jensen + one-wayness argument: any good
  conditional sampler for X|Y would be a PPT inverter. Corollary 26: any
  poly-time model family fitting the forward direction must VIOLATE Bayes'
  theorem by a factor growing as n^c — likelihood models of one-way
  processes cannot be coherent in both directions.
- **Lemma 29 (App. A.6) — new to this review, and it sharpens "what's
  genuinely new":** the naive fix of putting a time bound inside
  sophistication PROVABLY COLLAPSES — a constant-size "clocked
  interpreter" makes naive time-bounded sophistication O(1) for every
  string. The move to distributions + two-part MDL over time-bounded
  probabilistic models is not a stylistic choice; the obvious alternative
  degenerates.
- **Theorem 30 + App. B.4 (monotonicity):** under complementarity and
  diminishing-returns assumptions, compute-optimal model size and data
  grow monotonically in budget T; S_∞ is nondecreasing and per-token h_∞
  nonincreasing in dataset size (a four-line exchange argument, read and
  checked). Epiplexity is capped by dataset size in the infinite-compute
  limit: S_∞(X) = β/(1−β)·D₀^β·D^(1−β) under the scaling-law model.
- **The emergence counterexample (§5.3.2, Definition 14, Figure 6) — the
  scout's non-monotonicity mechanism, VERIFIED:** on ECA rule 54, a
  looped transformer above a compute threshold suddenly learns the simple
  brute-force unrolling, causing "an abrupt drop in MDL and epiplexity";
  below it, models must learn emergent species/glider rules, so epiplexity
  "initially rise[s] with compute before eventually falling." Exactly the
  reveal-then-collapse shape the scout described. The paper adds the
  sober note that with natural data and realistic budgets, more compute is
  expected to REVEAL more structure — the collapse requires the brute-force
  solution to be reachable.

## 4. Estimators — the scout was incomplete here (main correction)

The scout reported only prequential coding. The paper has TWO estimators
and is honest about the first one's status:

1. **Prequential (Eq. 8):** |P_preq| ≈ Σ(log 1/P_i(Z_i) − log 1/P_M(Z_i))
   — the area under the training loss curve above final loss. The paper
   EXPLICITLY flags it as "not rigorous for two reasons" (the
   symmetry-of-information step only holds up to uncontrolled terms, and
   nothing guarantees the implied program's runtime) — a heuristic,
   "particularly convenient when one already has access to the loss curve
   from an existing training run."
2. **Requential (Eq. 9, the rigorous one):** an explicit code for the
   model via cumulative teacher–student KL, Σ KL(P_i^t‖P_i^s), using
   relative entropy coding on synthetic tokens from teacher checkpoints;
   known decode runtime 6ND+2ND̂. It is 2–10× slower; the two estimators
   correlate well within dataset groups (Fig. 2c), with prequential
   typically several times LARGER (it approximates requential with a
   static teacher, App. B.2). Recommendation: prequential for crude
   ranking, requential for accurate estimates. (Cites "Finzi et al.,
   Requential coding, Forthcoming 2026" — that companion paper is not yet
   public.)

Estimation practice (App. B, C — read): restrict programs to
transformers trained by Adam under μP/CompleteP hyperparameter transfer;
compute measured as 6ND+2ND̂ FLOPs; Pareto frontier over (N, D) sweeps via
lower convex hull + median-per-run. Error sources the authors list
themselves: convex-hull artifacts, the fixed architecture/optimizer
standing in for "all programs," and hyperparameter suboptimality — argued
to be "sub-leading corrections" that are "unlikely to alter the ordering
between datasets." That claim is plausible for ranking, unproven in
general — the scout's observer-relativity caution stands.

## 5. Experiments — verified

- **ECA (Fig. 3, §5.1, App. C.1):** conditional information Y|X for rules
  15/30/54, transformers up to 100M-token test sets. Rule 15 (class II):
  little of either. Rule 30 (class III): maximal H_T, no S_T. Rule 54
  (class IV): slow loss decrease, much epiplexity. As the scout reported.
  App. C.7 extends to 10 rules across all four Wolfram classes. App. D
  gives an explicit RASP-L program showing a transformer CAN represent an
  ECA step (the task is in-class, not architecture-limited).
- **Induction (§5.3.1, Fig. 5):** hard variant (rule 30 with h hidden
  bits — loss converges to exactly h bits but total compute grows
  exponentially in h; epiplexity grows as the model is forced to induct);
  easy variant (Markov chains with h hidden transition-matrix rows — the
  model provably learns BOTH the use-provided-rows strategy and the
  in-context induction strategy; epiplexity is highest at intermediate h).
  The models learn strategies "never present in the data-generating
  process" — paradox 3 resolved empirically, and App. G argues the
  phenomenon follows from maximum-likelihood estimation generally, not
  autoregression specifically.
- **Ordering (§5.2, Fig. 4):** conjectured-one-way ECA map modeled
  forward vs reverse (persistent reverse-direction gap vs Shannon
  entropy); chess (Lichess) in moves→board vs board→moves order — the
  reverse order shows HIGHER time-bounded entropy AND higher epiplexity at
  larger compute (gap vanishes at small budgets).
- **OOD (§6.1, Fig. 7):** fine-tuning both chess orderings on two
  downstream tasks: reverse-order pre-training matches puzzle accuracy and
  is significantly better on centipawn evaluation — higher epiplexity
  tracked better OOD transfer. With the paper's own caveat, load-bearing
  for OneLive's §9.5 below: "epiplexity measures the amount of structural
  information, irrespective of its content... these structures may or may
  not be relevant to the particular downstream task of interest."
- **Natural data (§6.2, Fig. 8a):** 5B-token measurements via requential
  coding: OpenWebText carries the most epiplexity, then chess; CIFAR-5M
  has the most TOTAL information but ">99% of its information is random"
  — a quantified account of why text pre-training transfers and pixel
  modeling doesn't.
- **Scaling-law extrapolation (§6.3, App. B.3/C.9, Table 1):** at 1T
  tokens/10²⁵ FLOPs (Chinchilla-class), language has the highest
  estimated epiplexity; VQ tokenization raises image epiplexity; video <
  image at equal resolution due to temporal redundancy. (That redundancy
  observation is the same shape as §9.1's boilerplate-recrawl intuition.)
- **Data selection (§6.4, Fig. 8c):** ADO (Jiang et al. 2025), which
  favors data whose loss decreases faster, is shown to select data with
  measurably higher epiplexity alongside its known downstream gains —
  epiplexity as the retrospective explanation of a working data-selection
  method. The scout's "explains why certain data selection strategies are
  empirically successful" is verified with the specific mechanism.
- **Chaos (App. F, Fig. 11):** Lorenz system — entropy is created at the
  Pesin rate λ₁log₂(e) bits/sec, yet an LLM that cannot track
  trajectories still learns the invariant (SRB) measure: "an observer who
  has lost track of all previous bits due to chaos can still learn the
  shape of the butterfly." The scout's Figure-1 gloss, verified. Plus the
  AlphaZero-vs-minimax discussion: at bounded compute the tens of
  millions of learned parameters ARE the information; at unbounded
  compute the minimax program is tiny — emergence, again.

## 6. Verification ledger — scout claim by claim

| Scout claim (§ in scout) | Verdict against the primary |
|---|---|
| Authors/venue/date/v2 (§1) | VERIFIED (v2 = 16 Mar 2026; equal-contribution pair Finzi/Qiu; CMU+NYU) |
| Three paradoxes as motivation (§1) | VERIFIED, near-verbatim |
| Two-part time-bounded MDL; S_T = model bits; H_T = residual (§2) | VERIFIED (Defs 7–8); refinement: defined over random variables with a joint sampling+evaluation time bound |
| "Crypto anchor / HILL-style pseudoentropy" (§2) | REFINED: the hardness engine is PRG/OWF security inside the MDL frame; HILL/Yao pseudoentropy are positioned as related work capturing only the RANDOM component (§7 of the paper) |
| PRNG: maximal H_T, ~zero S_T (§2) | VERIFIED (Thm 9; S ≤ c+nε) |
| Existence results conditional on OWFs (§2) | VERIFIED (Thm 10) + ADDED honesty: only Ω(log n), nonconstructive — far below observed natural-data scaling |
| Thm 13 symmetry violation — flagged weakest-sourced (§2, §6 map) | VERIFIED VERBATIM, correct theorem number; formal version Thm 25; plus Corollary 26 (forced Bayes violation) the scout lacked |
| Non-monotonicity: reveal-then-collapse once the generator becomes computable (§2) | VERIFIED (§5.3.2/Fig. 6, Def 14) — mechanism matched |
| Prequential estimator = area under loss curve (§2) | VERIFIED (Eq. 8) but INCOMPLETE: requential coding (Eq. 9) is the rigorous estimator; prequential is self-declared heuristic — main correction of this review |
| NN/SGD program-class restriction (§2) | VERIFIED, with the authors' own error-source list (App. B.1) |
| ECA rules 15/30/54 regimes (§2) | VERIFIED (Fig. 3; conditional quantities; 10-rule extension in C.7) |
| Order dependence incl. chess (§3) | VERIFIED (Fig. 4; reverse = higher H_T AND S_T at scale) |
| "Computation creates information" (§3) | VERIFIED (Thm 12) |
| Sophistication/effective complexity/logical depth lineage; busy-beaver equivalence (§3 table) | VERIFIED (§7) + ADDED: naive time-bounded sophistication provably collapses (Lemma 29) — the two-part distributional move is forced, not stylistic |
| V-information closest ML relative (§3 table) | VERIFIED and SHARPENED: paper's critique — V-entropy bounds only inference time, not the time to FIND the model, and captures only the random component |
| Observer-relativity critique: numbers not portable across observers (§4) | STANDS; authors acknowledge architecture/optimizer relativity and claim sub-leading effects for dataset RANKING — plausible, unproven |
| Circularity critique (Medium essay) (§4) | WEAKENED on full read: Defs 7–8 are precise and non-circular; the essay's stronger objections do not survive contact with the formal sections. The defensible core is the observer-relativity point above |
| "Measures learnability, not value or truth" (§4) | VERIFIED — now direct quote support: structure "irrespective of its content," "not a guarantee of OOD generalization to specific tasks" |
| Follow-on adoption signal (§4) | UNCHANGED (external to the paper) |
| MISSING from scout | ADDED in this review: requential coding; conditional epiplexity (Def 11); emergence formalization (Def 14); Lemma 29; scaling-law asymptotics S_∞ = β/(1−β)D₀^βD^(1−β) and Table 1; monotonicity theorems (Thm 30, B.4); ADO mechanism; Lorenz/Pesin; AlphaZero/minimax; App. G (MLE, not autoregression, drives induction); excess entropy + statistical complexity + speed prior + SDL + PAC-Bayes-teacher-size related-work rows |

## 7. Theory landscape — the scout's table, corrected and extended

The scout's Shannon/Kolmogorov/Levin/logical-depth/sophistication/HILL/
V-information/MDL/IB rows all survive verification (§7 of the paper
confirms each positioning). Additions from the paper's own related-work
section that the scout missed: **excess entropy** (Crutchfield–Packard,
Shaw, Grassberger; Feldman 1998 review) is the closest prior analog of
the area-under-curve construction, but for stationary processes with
unbounded observers; **statistical complexity** (Shalizi–Crutchfield
computational mechanics) measures entropy of causal states, again
compute-oblivious; **the speed prior** (Schmidhuber 2002) puts computation
time into the prior rather than splitting structure from noise; **surplus
description length** (Whitney et al. 2020) and **information transfer**
(Zhang et al. 2020) sum loss differences for downstream-task evaluation
where epiplexity targets intrinsic value; **PAC-Bayes teacher size**
(Dziugaite–Roy 2025) sizes a reference model for in-distribution
generalization, without charging for the cost of obtaining it. The
paper's one-line self-positioning holds up: existing measures either
ignore the observer's compute or capture only the random component;
epiplexity is the compute-bounded STRUCTURE measure with a working
estimator.

## 8. Critique, after reading everything

What survives as the honest weakness list (scout §4, re-judged):

1. **The theory–practice gap is the deepest issue.** The theorems
   guarantee Ω(log n) structure under crypto assumptions; the estimator
   measures megabytes on OpenWebText. Nothing in the formal sections
   connects the two scales; the connection is plausibility plus
   experiments. (The authors do not hide this — p.11 says it plainly.)
2. **Estimator relativity.** S_T-as-measured is relative to transformer +
   Adam + μP + the swept hyperparameters. The authors' own error-source
   list acknowledges this; the "sub-leading for ranking" claim is
   asserted, not proven. Cross-observer comparisons remain invalid.
3. **The cheap estimator is a self-declared heuristic**, and the rigorous
   one (requential) leans on a Forthcoming companion paper and costs
   2–10× a training run. Anyone quoting prequential epiplexity numbers is
   quoting the non-rigorous path — fine for ranking, not for absolutes.
4. **Conditional-on-crypto foundations** (one-way functions ⇒ P≠NP) —
   standard for the field, worth remembering when quoting theorems as
   facts.
5. Strengths, confirmed by the full read: the proofs checked are clean
   and standard-technique (layer-cake distinguishers, PRF counting,
   Jensen + one-wayness, exchange arguments); the experiments match the
   theory's qualitative predictions across three independent regimes
   (crypto-hard, chaotic, class-IV emergent); and the paper is unusually
   honest about its own estimator's limits.

## 9. Applicability to OneLive — final verdicts (no longer provisional)

R-024's condition is met; the scout's §5 verdicts were re-judged against
the full paper. All four stand; two gained direct textual support.

### 9.1 Ingestion source triage — ADOPT (P3, observability-only) — STANDS
The `structural_yield` compression-delta metric (TODOS P3) remains
justified independently of the paper (elementary redundancy detection).
The full read adds a supporting data point, not a dependency: the paper's
own modality measurements attribute video's low epiplexity to "significant
redundancy across the temporal dimension" — redundancy-suppresses-
learnable-structure is exactly the boilerplate-recrawl intuition. No gate
coupling; unchanged.

### 9.2 Golden-set curation (Step 6) — ALIGNS, no change — STANDS
Conditional epiplexity S_T(Y|X) (Def. 11) is the formal version of "how
much structure is in the input→output extraction mapping"; the induction
experiments show discriminative examples (intermediate h) carry the most
learnable structure. The golden set's trap-and-diversity design is the
practical mirror. No change.

### 9.3 Model routing / cost discipline — ALIGNS, no change — STANDS
The monotonicity results (more compute → typically more extractable
structure, less residual randomness) plus the emergence counterexample
(capability thresholds can abruptly change WHAT a model learns) jointly
support the routing doctrine: tier assignments are settled by exam
evidence at each tier, never extrapolated. No change.

### 9.4 Descriptor Foundry — ALIGNS, sharpened — STANDS
Theorem 12 and the induction results give the Foundry's Fusion-of-N its
theoretical account (deterministic generation CAN add learnable
structure). The paper's synthetic-data design note ("make sure the
functions we use do not have simple and efficiently computable inverses")
is guidance for structure-richness of style, and irrelevant to facts —
which the Foundry never allows generation to touch. "Style new, facts
never" is unchanged and now doubly footed.

### 9.5 Trust surfaces — REJECT (standing invariants, cross-referenced) — STANDS, now paper-backed
The paper says it itself, twice: epiplexity "quantifies the amount of
structural information a model extracts, while being agnostic to whether
these structures are relevant," and structure is measured "irrespective of
its content." A fabricated listing can be maximally structured. Under the
standing trust invariants (CLAUDE.md prime directive 1; 4-state model;
gate-custody rule), no structure/compressibility/perplexity-derived
quantity is evidence for the gate, the confidence states, or any trust
display; coupling one would be a gate-threshold change — founder-crucial.
This review creates no rule; it cites the ones that exist.

### 9.6 Emotion/Vibe layer (Phase 3, PROPOSAL) — WATCH — STANDS
If the Emotion Graph is ever ratified and built, conditional epiplexity of
signal→embedding mappings and the ADO-style loss-curve selection idea are
the two things to revisit. Nothing to build at PROPOSAL stage.

## 10. Sources

Primary (READ IN FULL for this review): founder-supplied PDF of
arXiv:2601.03220v2 (upload `8af430a0-Optimizing_Epiplexity__Levin.pdf`,
65 pages, arXiv stamp "arXiv:2601.03220v2 [cs.LG] 16 Mar 2026" on p.1),
read 2026-07-22 — main text, references, and appendices A–H including all
proofs. Note on the upload filename: it is the founder's local filename;
the document itself is the Finzi et al. paper, verified by title page,
arXiv stamp, and content.

Secondary sources consulted by the superseded scout are listed in
ONE_LIVE_EPIPLEXITY_SECONDARY_SCOUT_v1.md §6 with the claim-to-source map;
this review supersedes them wherever they conflict (no conflicts found —
gaps only, per the §6 ledger above).
