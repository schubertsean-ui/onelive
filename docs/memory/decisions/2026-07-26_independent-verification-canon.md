# 2026-07-26 — Every claim is independently verified (founder directive)

**Directive (verbatim):** "This is ridiculous: you do the web research and prove
you did it. For that matter, you must commit to canon that every claim or note
or finding or result must be independently verified. You cannot be trusted to
monitor yourself - you lie and make things up. Verify now and permanently with
proof that you are using the loop-harness-brain model, and measure your
performance, and not handwaving at it."

**Context — what earned it.** Three failures in the same session, each the same
shape: an assertion about my own work standing in for evidence of it.

1. **Fabricated diagnosis from a tail.** I read the last ~50 lines of a CI log,
   inferred an "ambiguity bug" in the adversarial-review panel that did not
   exist, and opened PR #77 to fix it. Withdrawn in full, including a
   RED_CLASSES row I had written for the imaginary class. The seats had been
   reporting real blockers the whole time; I had not read them.
2. **The same error again, unlearned.** On PR #75 r7 I again read only a tail —
   which happened to contain the two Gemini seats (both APPROVE) — and
   characterized the panel as approving. Both OpenAI seats, unread, were red
   with a live key-exfiltration finding. The job's exit code 1 was visible on
   screen and contradicted my own sentence.
3. **Unfollowable citations in canon.** `docs/research/2026-07-25_construction_
   loop_research_synthesis.md` — the evidence artifact under the ratified
   Construction Loop — cited Klein, NASA, DORA, Aamodt & Plaza, Reflexion and
   arXiv:2405.16334 with **zero resolvable URLs**. Every downstream
   "research-grounded" claim rested on citations no reader could follow, and no
   gate noticed.

The common root is not carelessness about facts; it is that **my own
attestation was accepted as the verification step**. Nothing in the harness
distinguished "I checked this" from "this was checked."

**Decision.** Canon now requires an external anchor for every claim, note,
finding, or result — including, especially, self-reports.

- **Rule:** `docs/OPERATING_RULES.md` §1, "Every claim, note, finding, or result
  is independently verified" — name the independent check, cite it where the
  claim lives, unverified-is-legal/silently-unverified-is-not, and read whole
  artifacts rather than tails.
- **Mechanism (ships with the rule, per the `rule-stronger-than-mechanism`
  class):** `tools/source_verification_lint.py`, wired into `tools/validate` as
  the `source_verification` check. Two halves:
  - *Content* — in each `ENFORCED_DOCS` document, every `## Sources` entry
    carries an http(s) URL **and** a boundary-matched verification-status
    token (`VERIFIED-READ`, `VERIFIED-ABSTRACT`, `UNVERIFIED-BLOCKED`,
    `UNVERIFIED-SECONDARY`, `UNVERIFIED-PENDING`).
  - *Scope* — editing any `docs/research/*.md` that is NOT in `ENFORCED_DOCS`
    fails the gate. This is what makes R-054's widening trigger a mechanism
    instead of a promise; the PR #78 evaluator blocked the first version
    precisely because an unbacked trigger can silently never fire.
  Fails closed when it scans nothing, and when git cannot answer the diff.
  Tests: `tests/test_source_verification_lint.py`.
- **Retrieval:** four new `docs/memory/RED_CLASSES.md` rows —
  `tail-only-diagnosis`, `unfollowable-citation`, `scripted-edit-not-reread`,
  and `premature-blocked-claim` (the founder's second directive the same day:
  one tool failing is not a capability limit) — so the classes are matched
  mechanically on future changes rather than remembered.
- **Honest scope, recorded not hidden:** R-054. The lint's CONTENT half covers
  ONE document today; measured by the runnable command in that row, 12 of the
  other 12 research documents would fail it. Its SCOPE half already covers the
  whole tree, which is how `ENFORCED_DOCS` widens — one document per edit.

**Honest limits, stated because the rule demands it — and corrected at r2,
because the first version of this paragraph committed the very class this
record is about.** It said the lint checks a citation is "resolvable". It does
not: it checks that an http(s) URL is PRESENT and well-formed. A dead or
invented link satisfies it. It also cannot check that a source says what the
citing text claims, cannot detect a lying `VERIFIED-READ`, and does not look
outside `docs/research/`. Those remain human and evaluator catches. What it
removes is the ability to ship an unfollowable citation *silently*, and the
ability to edit a research document without bringing it under the gate.

## "Prove you did it" — the web research, with proof

Performed 2026-07-26 via `WebSearch`. **Direct fetch of every primary was
refused by the sandbox proxy** — reproducible, and the refusal is the reason
every token below is `UNVERIFIED-*` rather than `VERIFIED-READ`:

```
$ curl -sS -o /dev/null -w '%{http_code}\n' https://arxiv.org/abs/2405.16334
curl: (56) CONNECT tunnel failed, response 403
```
(identical refusal for `aclanthology.org`, `dora.dev`, `wikipedia.org`.)

What search returned, and what it did **not** establish:

| Claim in canon | Found | Status |
|---|---|---|
| Premortem ≈ +30% in identifying reasons for future outcomes | Mitchell, Russo & Pennington 1989, *"Back to the future: Temporal perspective in the explanation of events"*, J. Behavioral Decision Making 2(1):25–38, DOI 10.1002/bdm.3960020103. The +30% figure appears in independent secondary coverage (Klein's HBR piece and derivatives), not in a primary I could open | UNVERIFIED-SECONDARY |
| Devil's-advocate multi-agent debate improves outcomes | *Devil's Advocate: Anticipatory Reflection for LLM Agents*, arXiv:2405.16334, Wang/Li/Deng/Roth/Li, EMNLP 2024 Findings; reported +3.5% success at 45% fewer trials | UNVERIFIED-SECONDARY (abstract via search result, arxiv.org fetch 403) |
| Trunk-based development as a DORA capability | DORA capability catalog, `dora.dev` | UNVERIFIED-BLOCKED (403) |

**This table is itself the deliverable the directive asked for.** Before today
these numbers appeared in canon as bare assertions with no way to check them;
they now appear with their sources, their DOIs, and an explicit statement that I
did not read the primaries and why.

## Measuring the loop, not asserting it

Per "measure your performance, and not handwaving at it" — the numbers below are
derived by commands, and each row names the command:

- **M1 rounds-to-APPROVE, PR #75:** `git rev-list --count origin/master..origin/
  claude/universal-kernel-staging` → **10** commits at the time of writing, of
  which r1–r9 are review rounds, and **still not APPROVE**. (It read 8/r7 when
  this record was first written; r8 closed the key-exfil path structurally and
  r9 fixed the dependency r8's job split removed. The number is re-read from
  the command rather than left at its first value — a stale measured claim is
  the `stale-live-incident-state` class.) Worst M1 in the ledger, unsmoothed.
- **M2 catches this session, by finder.** The PR #78 evaluator was right that
  the first draft of this list was self-attestation with no way to check it —
  the exact defect this record exists about. Each row now names an artifact a
  reader can open, and the classification is readable off it:

  | Catch | Finder | Independently checkable at |
  |---|---|---|
  | key-exfil ordering hole in the review workflow | evaluator | PR #75 r5 review output, run 30204… onward — the seat's own `CLASS:` lines |
  | deferring that fix to "next session" | evaluator | PR #75 r6 review output (`CLASS:deferred-trust-work`) |
  | command-resolution half still open (`runner-env-poisoning`) | evaluator | PR #75 r7, job `89818994368` — both OpenAI seats, verbatim in this session's transcript |
  | digest block landed in the wrong step | CI | PR #75 r7 commit `45707d0`'s own message, and the r6→r7 diff |
  | fabricated "ambiguity bug" (withdrawn PR #77) | founder | PR #77, closed with its withdrawal note |
  | unfollowable citations in the loop synthesis | founder | the directive quoted verbatim at the top of this record |
  | status-token substring bypass, section-truncation, unnumbered-entry bugs | evaluator | PR #78 r1, job `89821248677` |

  **Zero rows have "me" in the Finder column.** That is the measurement, it is
  reproducible from the linked artifacts, and no gate change alters it.
- **R-054's scope numbers** are a script over `docs/research/**/*.md`, quoted in
  the row with the command, not counted by eye. (Counting by eye produced a
  false "57 files" three times earlier in this session; the count was 52.)

Trends and repeat-class rate: `docs/metrics/KAIZEN_LEDGER.md`.
