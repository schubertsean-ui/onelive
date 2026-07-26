# Research synthesis — closed-loop AI-agent code construction (Contract #24)

Greppable summary: the evidence base behind `docs/skills/construction_loop.md`
(founder-ratified charter canon 2026-07-25). Produced by the Contract #24
research pass; committed verbatim as the loop's cited evidence artifact
(#67 r4 nit: a cited synthesis must have an explicit in-repo location).
Context: the target failure mode was defects caught downstream by the
adversarial reviewer over 15 rounds (PR #65) because known failure
classes stored in the ledger were not retrieved before design.

## Stage 1 — Confirm vision, goals, specific objectives

Strongest practices: Toyota **A3/PDCA** structured problem framing —
background, current condition, target condition, and gap on one page
before any countermeasure (leantps.ca/lean-tps-a3-pdca-report-structured-thinking;
orcalean.com "Toyota's A3 thinking and root cause analysis"); and
**spec-driven development (SDD)** — a version-controlled spec, not the
code, as the source of truth (thebcms.com/blog/spec-driven-development;
the 30+-framework map, medium.com/@visrow). Mechanism: an explicit
target condition and gap statement makes success criteria checkable and
prevents solving the wrong problem — A3's known failure mode is being
treated as a checklist rather than thinking.

## Stage 2 — Assess green/red probable paths

Strongest practices: Gary Klein's **premortem** (HBR 2007); its
empirical base, Mitchell, Russo & Pennington (1989): prospective
hindsight raises correct identification of outcome reasons ~30%
(corporate.jasoncollins.blog/premortem; Klein's own effectiveness
paper). For rigor: **fault-tree / event-and-causal-factor structure over
5-Whys** — NASA mishap practice (NASA RCA overview, dbmteam.com; NASA
RCAT, nsc.nasa.gov/RCAT; KSC RCA-methods comparison) because 5-Whys
forces a single causal chain while real failures are multi-branch. The
agentic instantiation: **"Devil's Advocate: Anticipatory Reflection for
LLM Agents"** (EMNLP 2024 Findings, arXiv:2405.16334) — reflecting on
potential failures BEFORE action beats purely post-hoc reflection.
Mechanism: declaring failure as fact legitimizes dissent; a tree
prevents anchoring on the first plausible cause.

## Stage 3 — Check memory for green examples and red classes

Strongest practices: classic **CBR** — Aamodt & Plaza's
Retrieve→Reuse→Revise→Retain (iiia.csic.es/~enric/papers/AICom.pdf),
long applied to software knowledge reuse; modern agentic descendants:
**Reflexion** (arXiv:2303.11366 — verbal self-reflections in an episodic
buffer conditioning the next attempt), **Voyager** (compounding skill
library of verified successes), **ExpeL** (arXiv:2308.10144 — contrasts
successful vs failed trajectories, abstracts rules, INJECTS retrieved
insights + top-k similar trajectories at inference), **Agent Workflow
Memory**. Mechanism — the load-bearing finding: these systems improve
without weight updates ONLY because retrieval is wired into the loop
before planning. A lesson that exists but is not injected into the
design context is, functionally, not known.

## Stage 4 — Select the most likely success path(s)

Strongest practices: **Large Language Monkeys** (arXiv:2407.21787):
coverage scales log-linearly with independent samples (SWE-bench Lite
15.9%→56% at 1→250 samples) — but only where a cheap reliable verifier
exists; wider-vs-deeper studied directly (arXiv:2503.04412);
**Refine-n-Judge** (arXiv:2508.01543); LLM-judge panel survey
(github.com/CSHaitao/Awesome-LLMs-as-Judges); **bandit-based
configuration selection** (BOAD, arXiv:2512.23631). Decision rule:
generate N independent candidates when the verifier is mechanical and
failure modes diverse; iterate one when feedback is rich and
directional; a retrieved green precedent collapses the search to
reuse-with-revision (the CBR Reuse step).

## Stage 5 — Instruct and run agents; gather feedback

Strongest practices: **DORA capabilities** — working in small batches,
trunk-based development, continuous integration
(dora.dev/capabilities/) — among the strongest measured predictors of
delivery speed AND stability. Mechanism: small batches catch each
defect close to its cause with minimal blast radius — the direct
antidote to multi-round review churn, which is batch size exceeding
what one review round can converge.

## Stage 6 — Analyze, score, commit to memory

Strongest practices: **Google SRE blameless postmortem culture**
(sre.google/sre-book/postmortem-culture + workbook) and the **Army AAR**
(FM 7-0 Appendix K). Critical findings on knowledge that doesn't
transfer: postmortems without follow-through create an illusion of
improvement and most action items die within two weeks (incident.io SRE
postmortem practices); SRE's fix is staffed closure of action items;
the Army's fix is that lessons must change the next training plan, not
sit in a repository (thesystemsthinker.com on AARs). Mechanism: a
lesson transfers only when converted from prose into something the next
loop iteration mechanically consumes — a gate rule, an indexed token, or
a regression case.

## Stage 7 — Repeat; measure improvement or slippage

Strongest practices: PDCA Check/Act instrumented with DORA-style trend
metrics and the SRE warning about the unvirtuous cycle of unclosed
postmortems. Mechanism: improvement claims are trustworthy only when a
per-iteration metric exists whose slippage triggers action.

## The 3 highest-leverage changes for the specific failure mode

1. **Make memory retrieval a blocking gate, not a habit** (ExpeL/CBR:
   insights must be injected, never merely stored) — implemented as
   `tools/construction_gate.py` over `docs/memory/RED_CLASSES.md`.
2. **Seed the premortem from the ledger's red classes, run before
   design acceptance** (Klein's ~30% + anticipatory reflection) — the
   review shifts left from discovery to confirmation.
3. **Define "committed to memory" mechanically and trend
   repeat-classes** — gate rule / indexed token / regression case; the
   difference between a ledger and a brain.

## Sources

Added 2026-07-26 at founder direction ("every claim or note or finding or
result must be independently verified"). Until then this document cited
Klein, NASA, DORA, CBR and arXiv papers with **zero resolvable URLs** — the
"research-grounded" claim rested on citations no reader could follow, and no
gate noticed. `tools/source_verification_lint.py` now fails closed on that.

**Status tokens are literal and honest.** This sandbox's egress proxy refuses
direct fetches to every external host tried (`curl: (56) CONNECT tunnel
failed, response 403` against arxiv.org, aclanthology.org, dora.dev and
wikipedia.org on 2026-07-26), so no primary full text has been read from
here. Search-engine retrieval DOES work, which is how identity, venue and
authorship below were confirmed. Anyone with normal browser access can close
these out; the token is the honest statement of what was actually checked.

- Mitchell, D. J., Russo, J. E., & Pennington, N. (1989), "Back to the
  future: Temporal perspective in the explanation of events", *Journal of
  Behavioral Decision Making* 2(1) —
  <https://onlinelibrary.wiley.com/doi/abs/10.1002/bdm.3960020103> —
  **UNVERIFIED-SECONDARY** (paper identity, authors and journal confirmed via
  search; the +30% prospective-hindsight figure is reported consistently by
  independent secondary sources, e.g.
  <https://corporate.jasoncollins.blog/premortem>; Wiley abstract itself
  proxy-blocked).
- Klein, G. (2007), "Performing a Project Premortem", *Harvard Business
  Review* — <https://hbr.org/2007/09/performing-a-project-premortem> —
  **UNVERIFIED-BLOCKED** (canonical source of the premortem technique; not
  retrievable from this environment).
- Wang, H., Li, T., Deng, Z., Roth, D., & Li, Y. (2024), "Devil's Advocate:
  Anticipatory Reflection for LLM Agents", EMNLP 2024 Findings —
  <https://arxiv.org/abs/2405.16334> ·
  <https://aclanthology.org/2024.findings-emnlp.53.pdf> —
  **UNVERIFIED-SECONDARY** (arXiv id, title, authors and EMNLP-Findings venue
  confirmed via search; reported results — 23.5% success rate, +3.5% over
  zero-shot, 45% fewer trials/plan revisions — come from search synthesis,
  NOT from reading the paper).
- DORA, "Trunk-based development" capability —
  <https://dora.dev/capabilities/trunk-based-development/> —
  **UNVERIFIED-SECONDARY** (page exists; the small-batch/large-batch effect on
  change failure rate confirmed via search synthesis only).
- Aamodt, A., & Plaza, E. (1994), "Case-Based Reasoning: Foundational Issues,
  Methodological Variations, and System Approaches" (Retrieve→Reuse→Revise→
  Retain) — <https://www.iiia.csic.es/~enric/papers/AICom.pdf> —
  **UNVERIFIED-BLOCKED**.
- Shinn, N., et al. (2023), "Reflexion: Language Agents with Verbal
  Reinforcement Learning" — <https://arxiv.org/abs/2303.11366> —
  **UNVERIFIED-BLOCKED**.
- NASA root-cause analysis / causal-factor-tree practice —
  <https://nsc.nasa.gov/> — **UNVERIFIED-BLOCKED** (cited for the
  multi-branch-over-5-Whys argument).
