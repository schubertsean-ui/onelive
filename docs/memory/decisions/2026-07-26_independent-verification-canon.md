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
- **Retrieval:** new rows in `docs/memory/RED_CLASSES.md`, so the classes are
  matched mechanically on future changes rather than remembered. The list is
  deliberately NOT typed here — it read "three", then "four", then "five" as
  successive review rounds added classes, and each stale copy was correctly
  blocked as the retyped-evidence class this record exists about. Read it with
  `git diff origin/master -- docs/memory/RED_CLASSES.md | grep '^+| '`.
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

  Every row links the run that produced the finding, or the commit that
  carries it — an openable URL or a command that runs from a clone, never a
  prose reference (PR #78 r11, `CLASS:unfollowable-citation`, openai
  absence-only seat). The finding text is in the run's `adversarial-review`
  job log under the seat's own `CLASS:` line; the fix is the commit named
  beside it, readable offline with `git show <sha>`.

  | Catch | Finder | Independently checkable at | Fix |
  |---|---|---|---|
  | key-exfil ordering hole in the review workflow | evaluator | https://github.com/schubertsean-ui/onelive/actions/runs/30210106373 (review of head `8e56a20`) | `git show 1397458` |
  | deferring that fix to "next session" (`CLASS:deferred-trust-work`) | evaluator | https://github.com/schubertsean-ui/onelive/actions/runs/30210629877 (review of head `1397458`) | `git show 2a07458` |
  | command-resolution half still open (`runner-env-poisoning`) | evaluator | https://github.com/schubertsean-ui/onelive/actions/runs/30211733778/job/89818994368 — both OpenAI seats | `git show 06a1b11` |
  | digest block landed in the wrong step | CI | `git show 45707d0` and `git diff 2a07458 45707d0` | same commit |
  | fabricated "ambiguity bug" | founder | https://github.com/schubertsean-ui/onelive/pull/77 — closed with its withdrawal note | closed, not merged |
  | unfollowable citations in the loop synthesis | founder | the directive quoted verbatim at the top of this record | this record + `tools/source_verification_lint.py` |
  | status-token substring bypass, section-truncation, unnumbered-entry bugs | evaluator | https://github.com/schubertsean-ui/onelive/actions/runs/30212592813/job/89821248677 (PR #78 r1) | `git log --oneline origin/master..HEAD` |
  | status token read out of a QUOTED TITLE, and `_` outside the token boundary | evaluator | https://github.com/schubertsean-ui/onelive/actions/runs/30220698493 (PR #78 r10, head `8c4a4b0`) | this commit |

  **Zero rows have "me" in the Finder column.** That is the measurement, it is
  reproducible from the linked artifacts, and no gate change alters it.
- **R-054's scope numbers** are a script over `docs/research/**/*.md`, quoted in
  the row with the command, not counted by eye. (Counting by eye produced a
  false "57 files" three times earlier in this session; the count was 52.)

Trends and repeat-class rate: `docs/metrics/KAIZEN_LEDGER.md`.
