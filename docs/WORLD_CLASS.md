# 1Live — The World-Class Bar (per-clause cited)

> **Status:** Canonical acceptance contract for the 1Live build. Every clause is grounded in a named authority and/or institutional standard, with the exact source URL. Where a specific numeric claim could not be sourced from a fetched primary page, it is marked **n.a.** rather than invented.
>
> **Grounding basis (user directive):** *Both* named practitioners AND institutional standards. Sourcing rigor (user directive): *every clause cited.*
>
> **How to use this doc:** This is the "definition of done" the generator negotiates against *before* writing code (LOOPS §III), the checklist the independent evaluator grades against (LOOPS §II), and the bar every already-built component is retro-audited against. Nothing merges to `master` until (a) the user has ratified this bar and (b) a non-Claude reviewer has signed off against it.
>
> Compiled 2026-07-12. Evidence base: `onelive_worldclass_sources.md` (77 fetched URLs, 9 domains).

---

## §0 — Agent-process discipline (how the model is driven)

Grounded in **Andrej Karpathy — "LOOPS.md: Field Notes on Agents That Run for Days"** (independent research notes, v060726). This governs *how* 1Live is built by long-running agents, and is the layer the user caught us drifting from.

- **0.1 Write the loop, not the prompt.** "The unit of leverage stopped being the prompt the moment models became good enough to follow a procedure without supervision; what matters now is the procedure." The build runs as a standing loop (gather → reason → act → verify → repeat), not one-off prompts. (Karpathy, LOOPS §I)
- **0.2 Separate the roles — the generator MUST NOT grade itself.** "A generator that writes everything and is forbidden from grading its own work. An evaluator that reads diffs, launches `playwright`, plays the app… Mixing the roles is the most common failure I see; the model becomes sycophantic the moment it grades itself, and the loop quietly converges on slop." **1Live rule:** auth, pipeline, SQL, and data-trust changes require adversarial review by a **non-Claude** model (GPT-5.5) before merge. Claude never approves its own security-critical CL. (Karpathy, LOOPS §II)
- **0.3 Negotiate the contract first.** "Before the generator writes a single line, it proposes what done looks like and the evaluator pushes back… Twenty-seven criteria is a reasonable size for a small app; ten is usually too few and the evaluator rubber-stamps… This is the single change that moved my own runs from broken demos to working products." **1Live rule:** this document + `OPERATING_RULES.md` are the ratified contract; the generator does not get merge credit for work that pre-dates a ratified contract. (Karpathy, LOOPS §III)
- **0.4 Write to disk, not to context.** "Context windows lie. They compact, they rot, they hide what you said an hour ago behind a summary you did not write. A file on disk does not lie." **1Live rule:** `STATE.md`, session arcs, append-only feedback logs, and this contract are the source of truth — not conversation memory. (Karpathy, LOOPS §IV)
- **0.5 Let the loop restart; insert a human only when the contract is wrong.** "Do not interrupt [a clean-slate restart]. The restart is the loop working correctly. Insert a human only when the contract itself is wrong, not when the build is." (Karpathy, LOOPS §V)
- **0.6 Score the subjective with a written rubric.** "Taste is gradable if you write it down. Four axes, weighted: design, originality, craft, functionality… The model will not invent taste; it will only converge toward the taste you described." **1Live rule:** UX quality (§6) is graded against WCAG + Nielsen + Core Web Vitals, not "vibe." (Karpathy, LOOPS §VI)
- **0.7 Read the traces, not the summaries.** "Every debugging insight I have about agent loops came from reading the raw transcript, not from running another experiment… Skip this step and you are tuning by vibe." **1Live rule:** subagent output is graded from its raw diff + test logs, never from its own self-summary. (Karpathy, LOOPS §VII)
- **0.8 Delete the harness that has stopped reading.** "The harness that grows monotonically is a harness that has stopped reading. Re-read your harness against each new release and delete anything the model now does for free." **1Live rule:** each Kaizen pass includes a scheduled harness-pruning review, not only additions. (Karpathy, LOOPS §VIII)
- **0.9 The bottleneck always moves.** "When coding stops being the bottleneck, planning becomes the bottleneck. When planning is solved, verification becomes the bottleneck… If everything is going smoothly, you are not looking carefully enough." **1Live rule:** each session names the current bottleneck explicitly. (Karpathy, LOOPS §IX)

---

## §1 — Code quality

- **1.1 Small, self-contained changes.** "the right size for a CL is one self-contained change… 100 lines is usually a reasonable size for a CL, and 1000 lines is usually too large." ([Google eng-practices — Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html))
- **1.2 Small CLs are reviewed more thoroughly and introduce fewer bugs.** "Reviewed more quickly… more thoroughly… Less likely to introduce bugs… Simpler to roll back." ([Google eng-practices — Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html))
- **1.3 Design is the most important review criterion; be vigilant about over-engineering.** "The most important thing to cover in a review is the overall design." "'Too complex' usually means 'can't be understood quickly by code readers.'" ([Google eng-practices — What to look for](https://google.github.io/eng-practices/review/reviewer/looking-for.html))
- **1.4 Comments explain WHY, not what.** "comments are useful when they explain why some code exists… If the code isn't clear enough to explain itself, then the code should be made simpler." ([Google eng-practices — What to look for](https://google.github.io/eng-practices/review/reviewer/looking-for.html))
- **1.5 Good naming.** "A good name is long enough to fully communicate what the item is or does, without being so long that it becomes hard to read." ([Google eng-practices — What to look for](https://google.github.io/eng-practices/review/reviewer/looking-for.html))
- **1.6 Tests ship in the same CL and must be able to fail.** "tests should be added in the same CL as the production code." "Will the tests actually fail when the code is broken?" ([Google eng-practices — What to look for](https://google.github.io/eng-practices/review/reviewer/looking-for.html))
- **1.7 Self-testing code.** "you aren't really doing continuous integration unless you have self-testing code"; "assume that any non-trivial code without tests is broken." ([Fowler — Self Testing Code](https://martinfowler.com/bliki/SelfTestingCode.html))
- **1.8 Refactoring changes structure without changing behavior.** "a change made to the internal structure of software to make it easier to understand and cheaper to modify without changing its observable behavior." ([Fowler — Definition of Refactoring](https://martinfowler.com/bliki/DefinitionOfRefactoring.html))
- **1.9 Beck's Four Rules of Simple Design (priority order):** (1) Passes the tests; (2) Reveals intention; (3) No duplication; (4) Fewest elements. ([Fowler — Beck Design Rules](https://martinfowler.com/bliki/BeckDesignRules.html))
- **1.10 Manage complexity via deep modules & information hiding.** "It's more important for a class to have a simple interface than a simple implementation." Complexity = "change amplification," "cognitive load," "unknown unknowns," caused by "dependencies and obscurity." ([Ousterhout — Modular Design](https://web.stanford.edu/~ouster/cgi-bin/cs190-winter18/lecture.php?topic=modularDesign)) · ([A Philosophy of Software Design notes](https://books.danielhofstetter.com/a-philosophy-of-software-design/))

---

## §2 — Software architecture

- **2.1 Reliability, scalability, maintainability are the core goals.** "we need to build applications that are reliable, scalable and maintainable in the long run"; the essence is "mastering the tradeoffs." ([Kleppmann — DDIA](https://dataintensive.net/))
- **2.2 Stateless, share-nothing processes.** "Twelve-factor processes are stateless and share-nothing." "Sticky sessions are a violation of twelve-factor." ([12-Factor — Processes](https://12factor.net/processes))
- **2.3 Config in the environment, separated from code.** "stores config in environment variables"; litmus test: "the codebase could be made open source at any moment, without compromising any credentials." ([12-Factor — Config](https://12factor.net/config))
- **2.4 Decouple large domains via Bounded Contexts.** "DDD deals with large models by dividing them into different Bounded Contexts and being explicit about their interrelationships." ([Fowler — Bounded Context](https://martinfowler.com/bliki/BoundedContext.html))
- **2.5 Design against the AWS Well-Architected six pillars** (Operational excellence, Security, Reliability, Performance efficiency, Cost optimization, Sustainability). ([AWS Well-Architected — Pillars](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html)) · ([Definitions](https://docs.aws.amazon.com/wellarchitected/latest/framework/definitions.html))
- **2.6 Corroborated by Google Cloud Well-Architected pillars.** ([Google Cloud Well-Architected](https://cloud.google.com/architecture/framework))

---

## §3 — Tech stack / dependency choice

- **3.1 Explicitly declare and isolate dependencies.** "A twelve-factor app never relies on implicit existence of system-wide packages… declares all dependencies, completely and exactly." ([12-Factor — Dependencies](https://12factor.net/dependencies))
- **3.2 Keep a complete inventory of component versions** (client + server + nested); use OWASP Dependency-Check / retire.js. ([OWASP A06:2021](https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/))
- **3.3 Remove unused dependencies and features to minimize attack surface.** ([OWASP A06:2021](https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/))
- **3.4 Obtain components only from official sources; prefer signed packages.** ([OWASP A06:2021](https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/))
- **3.5 Patch in a risk-based, timely fashion; monitor CVE/NVD via SCA.** ([OWASP A06:2021](https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/))
- **3.6 Avoid unmaintained dependencies.** ([OWASP A06:2021](https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/))
- **3.7 Communicate change via Semantic Versioning** (MAJOR/MINOR/PATCH). ([SemVer 2.0.0](https://semver.org/))

---

## §4 — Security & auth (the fail-closed gate lives here)

- **4.1 Verify controls against OWASP ASVS.** ASVS "provides a basis for testing web application technical security controls." *(ASVS L1/L2/L3 numeric level definitions: not on fetched pages — **n.a.**)* ([OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/))
- **4.2 Fail closed / deny by default.** "an application should be configured to deny access by default." Failed checks must not "put the software into an unstable state that could lead to authorization bypass." ([OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html))
- **4.3 Defense in depth.** "Do not depend on any single framework, library, technology, or control to be the sole thing enforcing proper access control." → **This is why 1Live uses TWO independent layers (Next middleware + FastAPI JWT verify).** ([OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html))
- **4.4 Enforce authorization on EVERY request (least privilege).** "Validating permissions correctly on just the majority of requests is insufficient." ([OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html))
- **4.5 JWT: always verify signature; reject `alg=none`; pin expected algorithm.** ([OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html))
- **4.6 JWT: enforce short expiration + refresh/rotation.** ([OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html))
- **4.7 Clerk session JWT verification MUST validate: (1) algorithm, (2) signature via public key, (3) `exp`/`nbf`, (4) `azp` against known origins.** "Not setting [azp] can open your application to CSRF attacks." → **This is GAP 1; closed by `api/clerk_auth.py`.** ([Clerk — Manual JWT verification](https://clerk.com/docs/backend-requests/manual-jwt))
- **4.8 Passwords: length over complexity** (≥15 chars single-factor; ≥8 with MFA; permit ≥64; no composition rules). ([NIST SP 800-63B-4 §3.1.1.2](https://pages.nist.gov/800-63-4/sp800-63b.html))
- **4.9 No forced periodic rotation; force change on evidence of compromise.** ([NIST SP 800-63B-4 §3.1.1.2](https://pages.nist.gov/800-63-4/sp800-63b.html))
- **4.10 Verify the entire password; store salted + hashed.** ([NIST SP 800-63B-4 §3.1.1.2](https://pages.nist.gov/800-63-4/sp800-63b.html))
- **4.11 Screen against a compromised-password blocklist.** ([NIST SP 800-63B-4 §3.1.1.2](https://pages.nist.gov/800-63-4/sp800-63b.html))
- **4.12 Rate-limit authentication (≤100 consecutive failed attempts).** ([NIST SP 800-63B-4 §3.2.2](https://pages.nist.gov/800-63-4/sp800-63b.html))
- **4.13 Secrets in the environment (config litmus test).** ([12-Factor — Config](https://12factor.net/config))

---

## §5 — Data / ingestion trust & quality (1Live's core moat)

- **5.1 Provenance underpins trust.** "Provenance is information about entities, activities, and people involved in producing a piece of data… used to form assessments about its quality, reliability or trustworthiness." ([W3C PROV-Overview](https://www.w3.org/TR/prov-overview/))
- **5.2 Accuracy** = "closeness of data values to real values." ([DAMA — DDQ](https://www.dama-nl.org/wp-content/uploads/2020/09/DDQ-Dimensions-of-Data-Quality-Research-Paper-version-1.2-d.d.-3-Sept-2020.pdf))
- **5.3 Completeness** = "the degree to which all required data values are present." ([DAMA — DDQ](https://www.dama-nl.org/wp-content/uploads/2020/09/DDQ-Dimensions-of-Data-Quality-Research-Paper-version-1.2-d.d.-3-Sept-2020.pdf))
- **5.4 Consistency** across records/files/time comply with a rule. ([DAMA — DDQ](https://www.dama-nl.org/wp-content/uploads/2020/09/DDQ-Dimensions-of-Data-Quality-Research-Paper-version-1.2-d.d.-3-Sept-2020.pdf))
- **5.5 Validity, Uniqueness, Currency.** ([DAMA — DDQ](https://www.dama-nl.org/wp-content/uploads/2020/09/DDQ-Dimensions-of-Data-Quality-Research-Paper-version-1.2-d.d.-3-Sept-2020.pdf))
- **5.6 LLM extraction is not inherently reliable.** "LLMs are prone to hallucination, generating plausible yet nonfactual content." → **This is why AI never auto-promotes; multi-confirm gate required.** ([Huang et al., arXiv 2311.05232](https://arxiv.org/abs/2311.05232))
- **5.7 Guard both factuality and faithfulness hallucination.** Faithfulness = did the extraction stay true to the source document. ([Huang et al., survey PDF](https://arxiv.org/pdf/2311.05232))

---

## §6 — UX / UI

- **6.1 WCAG four principles (POUR):** perceivable, operable, understandable, robust. ([W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/))
- **6.2 Conformance levels A / AA / AAA;** target AA. ([W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/))
- **6.3 Minimum text contrast 4.5:1 (SC 1.4.3, AA).** ([W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/))
- **6.4 Nielsen's 10 usability heuristics** (system status; match real world; user control/freedom; consistency; error prevention; recognition over recall; flexibility; minimalist design; recover from errors in plain language; help/docs). ([NN/g — 10 Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/))
- **6.5 Core Web Vitals — LCP ≤ 2.5 s.** ([web.dev — Web Vitals](https://web.dev/articles/vitals))
- **6.6 Core Web Vitals — INP ≤ 200 ms.** ([web.dev — Web Vitals](https://web.dev/articles/vitals))
- **6.7 Core Web Vitals — CLS ≤ 0.1.** ([web.dev — Web Vitals](https://web.dev/articles/vitals))
- **6.8 Measure Core Web Vitals at the 75th percentile,** segmented mobile/desktop. ([web.dev — Web Vitals](https://web.dev/articles/vitals))

---

## §7 — Operationalizing / deploy / reliability

- **7.1 Monitor the Four Golden Signals:** Latency, Traffic, Errors, Saturation. ([Google SRE — Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/))
- **7.2 Define SLI / SLO / SLA.** ([Google SRE — SLOs](https://sre.google/sre-book/service-level-objectives/))
- **7.3 100% is the wrong target — use an error budget.** ([Google SRE — SLOs](https://sre.google/sre-book/service-level-objectives/))
- **7.4 Minimize toil** (manual, repetitive, automatable work). ([Google SRE — Eliminating Toil](https://sre.google/sre-book/eliminating-toil/))
- **7.5–7.8 Track the DORA four keys:** Deployment Frequency, Change Lead Time, Change Fail Rate, Failed Deployment Recovery Time. *(Elite/High/Medium/Low numeric thresholds: not on fetched page — **n.a.**)* ([DORA — Four Keys](https://dora.dev/guides/dora-metrics-four-keys/))

---

## §8 — Admin / moderation / human-in-the-loop

- **8.1 Log security-relevant & administrative events** (authN successes/failures, authZ failures, user-admin actions, privilege changes, UGC processing). ([OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html))
- **8.2 Each log event captures WHEN, WHERE, WHO, WHAT.** ([OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html))
- **8.3 Never log secrets or sensitive data** (session IDs, tokens, passwords, connection strings, keys, PII without consent). ([OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html))
- **8.4 RBAC: manage access by role, not per-user ACLs** (INCITS 359-2012). ([NIST — RBAC](https://csrc.nist.gov/projects/role-based-access-control))
- **8.5 Automate moderation only at high confidence; keep humans in the loop.** ([Santa Clara Principles](https://santaclaraprinciples.org/))
- **8.6 Notice: tell users what was actioned and why.** ([Santa Clara Principles](https://santaclaraprinciples.org/))
- **8.7 Appeal: independent human review by someone not involved in the initial decision.** ([Santa Clara Principles](https://santaclaraprinciples.org/))

---

## §9 — Testing & QA

- **9.1 The test pyramid** — many unit tests, few UI tests. ([Fowler — Test Pyramid](https://martinfowler.com/bliki/TestPyramid.html))
- **9.2 High-level tests are a second line of defense; broad-stack tests are costly/brittle.** ([Fowler — Test Pyramid](https://martinfowler.com/bliki/TestPyramid.html))
- **9.3–9.5 Google test sizes** — Small (no fs/network/db, <60s), Medium (local fs/net/db), Large (external systems). ([Google Testing Blog — Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html))
- **9.6 A test that cannot fail proves nothing — mutation testing is the gold standard.** "Traditional test coverage… does not check that your tests are actually able to detect faults." ([PIT — Mutation Testing](https://pitest.org/))
- **9.7 Coverage is a signal, not a target.** "high coverage numbers are too easy to reach with low quality testing." ([Fowler — Test Coverage](https://martinfowler.com/bliki/TestCoverage.html))
- **9.8 The real bar:** "You rarely get bugs that escape into production, and You are rarely hesitant to change some code for fear it will cause production bugs." ([Fowler — Test Coverage](https://martinfowler.com/bliki/TestCoverage.html))

---

## Self-audit: where 1Live stands against this bar (2026-07-12)

Retro-applied to what is already built. Verdicts are **claims until independently verified** (§0.7).

| Domain | Verdict | Evidence / gap |
|---|---|---|
| §0 Agent process | **Partial** | Strong on 0.4 (state on disk). Weak on 0.2 (all-Claude, no independent evaluator yet) and 0.3 (built before ratifying contract). 0.8 harness-pruning never done. |
| §1 Code quality | **Unverified** | 196+25 tests pass per subagent summary; not yet graded from raw diff by a non-Claude reviewer. |
| §2 Architecture | **Meets (design)** | Stateless FastAPI workers, env config, Supabase Postgres. Bounded contexts informal. |
| §3 Tech stack | **Meets** | Explicit manifests (package.json/lockfile, requirements). No SCA/CVE monitoring wired. |
| §4 Security/auth | **Meets by design, unverified in code** | Two-layer fail-closed gate + `azp` (4.7/GAP 1) specified and shipped in PR#9; needs non-Claude adversarial review. |
| §5 Data trust | **Strong** | Provenance columns, 4-state confidence, audit log, AI-never-auto-promotes, multi-confirm gate. Real sources: 230 + 37 new. |
| §6 UX | **Unverified** | No Core Web Vitals / WCAG contrast measurement yet. |
| §7 Ops | **GAP** | `/healthz` + audit trails only. No SLOs, error budget, golden-signal monitoring, or DORA metrics. |
| §8 Admin | **Partial** | Audit logging present; RBAC informal; no moderation appeal flow (low priority pre-launch). |
| §9 Testing | **Partial** | 221 tests + security gate. Zero mutation testing (9.6) → coverage is signal, not proof. |

**Named gaps to close (tracked, not silent):** independent non-Claude evaluator (§0.2); SLO/golden-signal observability (§7); mutation testing (§9.6); SCA/CVE monitoring (§3.5).
