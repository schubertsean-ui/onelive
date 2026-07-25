# RED_CLASSES — the machine-consumed red-class index (Construction Loop Stage 3/6)

Greppable summary: the retrieval index `tools/construction_gate.py` reads
(#67 r4: the blocking-retrieval rule ships WITH its mechanism; hardened
r5/r6). One row per distilled failure class; `triggers` are
comma-separated substrings matched case-insensitively against BOTH the
diff's changed file paths AND the diff's content (r6: semantic classes
match even when no path names them) — when a trigger matches, the
session contract (STATE.md) must carry a DELIBERATE citation on a line
ADDED by the current change, in the canonical form `[S3:<token>] <answer>`
(r5: never cumulative history; r6: a bare token in a changelog, comment,
or this very table is incidental text, not retrieval). Broad triggers
OVER-trigger by design — the cost is an extra citation line; the failure
mode this index exists to kill is under-triggering. SELF-PROTECTED (r6):
the gate compares this file against its base copy — deleting a token or
narrowing a trigger list fails validate closed (gate-threshold
relaxation, founder-crucial; a ratified removal edits the gate tool
itself in the same PR as its decision record). Tokens are never renamed
(history keys). Stage 6 discipline: every new evaluator/founder catch
adds or reinforces a row here IN THE SAME COMMIT as its Kaizen entry —
a class absent from this index is a prose-only lesson, an open defect.

| token | triggers | source |
|---|---|---|
| caller-suppliable-custody-inputs | publish_gate, autonomy, approve, custody | KAIZEN #65 r3/r11/r13 — keys, paths, state, clock, identity: the release subject must never choose a custody input |
| final-gate-trusts-generator | publish_gate, promote | KAIZEN #65 r4/r5 — the last gate re-derives facts/shape itself (total re-render), never trusts upstream ran |
| release-path-weaker-than-generation | generator, render, promote | KAIZEN #65 r7/r13 — every re-render/release path enforces at least generation's full contract |
| false-price-claim | price, carousel, copy | KAIZEN #65 r5 — exact-minimum framing, Decimal-exact labels, no truncation |
| semantic-claim-not-rederived | scenario, series, claim | KAIZEN #65 r8 — a claim's MEANING (predicates) is re-derived at custody, not trusted |
| fabricated-qualitative-copy | caption, hook, copy, overlay | KAIZEN #65 r11 — outward copy is canonical facts + curated nouns only |
| grant-not-content-bound | autonomy, grant, ratification | KAIZEN #65 r10 — grants bind renderer fingerprint, series, cadence |
| fail-open-on-custody-misconfig | publish_gate, autonomy, config | KAIZEN #65 r12 — a corrupt trust artifact refuses EVERYTHING, never gets ignored on another path |
| weak-key-accepted-at-custody | key, hmac, secret, sign | KAIZEN #65 r14 — key-strength floor at every sign/verify |
| volatile-safety-store | journal, ledger, store, cap | KAIZEN #65 r14 — safety counters require durability attestation |
| deferred-trust-work | TODOS, RECORD | KAIZEN #67 r1 — trust-path gaps ship in the PR that finds them, never park as TODO |
| retyped-evidence | changelog, STATE, KAIZEN | KAIZEN #35 family + #67 r1 — cite machine evidence, never hand-copy numbers |
| featurability-dimension-missed | jsonld, discovery, geo, markup | KAIZEN #67 r2 — every trust dimension (origin, status, confidence) at every public emitter |
| nonfinite-decimal-accepted | price, decimal | KAIZEN #67 r2/r3 — one shared normalizer; NaN/Infinity/negative refuse everywhere |
| swallowed-corrupt-data | filter, select | KAIZEN #67 r3 — corrupt data surfaces loudly, never silently filtered |
| stalled-state-needs-active-diagnosis | workflow, ci, cron | KAIZEN founder(Red) 2026-07-25 — a stalled external state gets one diagnostic probe, not more waiting |
| governance-ambiguity | decisions, CLAUDE, OPERATING | KAIZEN #67 r1 — precedent-bearing records state their precise scope |
| false-confidence-gate | tools, gate, lint | KAIZEN 2026-07-24 family — a gate's self-description never claims more than its implementation |
