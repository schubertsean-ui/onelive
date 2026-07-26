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
| fail-open-on-custody-misconfig | publish_gate, autonomy, config, trusted, preflight | KAIZEN #65 r12, BROADENED #72 r6 after it recurred past its marker — a custody mechanism that is corrupt OR MISSING refuses everything and never reaches a success path on any branch; the substrate is not just trust DATA (a malformed record) but trust TOOLING (an absent trusted-base script), and the fix is an invariant over the shape (every custody fetch fails closed, asserted by test) rather than a guard on one instance |
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
| self-weakenable-gate | construction_gate, red_classes, index | KAIZEN #67 r6 — a gate must not be silently weakenable through its own data; base-vs-head self-protection |
| rule-stronger-than-mechanism | skills, operating, canon, charter | KAIZEN #67 r4/r7 — a rule may claim exactly the mechanism that ships with it; unmechanized halves carry a RECORD row in the same commit |
| stale-live-incident-state | incident, arming, smoke | KAIZEN #43 arc — live-state claims re-verify against the live system, never against earlier prose |
| pushed-on-red | validate, commit, push | KAIZEN #65 r5-commit + #69 self-caught — validate runs unchained with its exit code checked explicitly; a pipe that masks FAIL is the defect |
| malformed-ledger-row | KAIZEN, ledger, metrics | KAIZEN #69 self-caught — ledger rows never contain raw pipes; parsers fail loud and the writer verifies by running them |
| nonfinite-numeric-accepted | weight, prior, seed, threshold | KAIZEN #69 r2 — every numeric config input checks math.isfinite, at every layer that claims to validate |
| stale-base-widens-range | validate, construction_gate, diff, base | KAIZEN #71 CI-caught — refresh the base ref before any range-derived gate; a stale base widens the range and can pass locally what CI correctly fails |
| workflow-tool-version-skew | workflows, .github, trusted, adversarial_review, model, constant | KAIZEN #71 CI-caught, BROADENED #72 r2 after it recurred past its first marker — NOTHING a PR changes in a base-owned trusted tool affects the run judging that PR: not new flags (feature-detect them), and not behaviour-bearing CONSTANTS such as the reviewer model (the PR-owned workflow must pin them, and a test must pin the workflow literal to the tool's own default so the pair cannot drift) |
| env-dependent-hermetic-test | tests, conftest, hermetic, fixture | KAIZEN #71 r9 self-caught — a test documented as hermetic must be RUN in the deprived environment (no network, no remote, no credentials) before that claim is made; a gate's precondition belongs at the point of use, never eagerly where supplied inputs make it unnecessary |
| missing-record-read-as-state | scorecard, metrics, KAIZEN, ledger, trend | KAIZEN #71 r10 — a derived metric states only what its source says; an absent record is reported AS ABSENT, never rendered as a confident status the tool cannot observe, and its coverage test asserts known facts rather than non-crash |
| unusable-credential-tier | model, api_key, seat, provider, quota | KAIZEN #72 r1/r3 — a minted credential is not a usable one, and a model name is never guessed from an error string: listing shows only what EXISTS — quota is invisible to it — so preflight the pin with a real minimal call before the gate depends on it, and print the advertised list so a wrong pin is fixed from evidence. An absent credential stays an explicit empty seat, never a red |
| untested-gate-branch | workflows, gate, preflight, tools | KAIZEN #72 r4 — a gate-custody mechanism ships with a committed test per BRANCH; local simulation is not repo-verifiable, and logic living inline in workflow YAML is untestable by construction — move it into a tool with an injectable transport |
| pagination-integrity-gap | paginate, pagetoken, cursor, registry, list | KAIZEN #72 r5 — a paged walk that a gate depends on must EXHAUST or fail loud (a cap is a runaway backstop, never a stopping point: a partial list is wrong evidence, not less evidence), and opaque cursor tokens are percent-encoded before entering a query |
| contract-scope-violation | STATE, contract, session | KAIZEN #72 r5 — when a build's real scope exceeds its session contract, AMEND the contract in the same push (quoting the original and the reason it moved); work that outruns its stated done-criteria cannot be reviewed against them |
| mutable-model-alias | model, alias, latest, version, pin | KAIZEN #72 r6 — a gate's model/version id is an IMMUTABLE concrete id, never a floating alias: an alias moves provider-side with no commit here, so review strength escapes repo custody. If only an alias is known to work, say ALIAS not pin, and carry a RECORD row with an objective trigger to concretise it |
