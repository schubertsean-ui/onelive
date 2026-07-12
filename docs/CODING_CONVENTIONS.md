# CODING_CONVENTIONS — reviewer-facing checklist

Greppable summary: standalone checklist consolidating the coding rules
already stated in `CLAUDE.md` and `docs/OPERATING_RULES.md` §1/§3 into one
place reviewers/personas actually check against. This doc does not add new
rules — it does not override or contradict either source; if this doc and
CLAUDE.md/OPERATING_RULES.md ever disagree, the latter two win and this doc
is stale and needs fixing.

Used by: `docs/review_personas/*.md` (each persona's checks map onto a subset
of this list) and `tools/agent_review` (prints the persona doc + diff for a
human/agent to review against this checklist).

## Trust & safety (highest priority — see OPERATING_RULES §0, §1, §3)

- [ ] No swallowed errors: `except: pass` / `except Exception: <blank>` is
      banned unless the caught branch is itself logged/audited with a comment
      justifying the swallow (`tools/lint.py` enforces this mechanically).
- [ ] Fail loudly on misconfiguration; only degrade safely on *transient*
      faults, and only with an audit/log line (`worker/resolve_entities.py`
      `_fuzzy_match`'s SQLSTATE 42883-vs-other-errors split is the reference
      pattern; `ai/claude_provider.py` mirrors it for `ExtractionConfigError`
      vs 429/5xx retry+degrade).
- [ ] The AI extraction step never promotes/publishes directly — it only
      proposes candidates; promotion always passes the multi-confirm gate
      (`worker/gating.py`), enforced by `tools/trust_gate.py`'s
      AI-never-promotes check.
- [ ] Every extraction/degradation/fuzzy-merge stage leaves an audit trail
      (`_provenance` on AI extractions; `audit_log` writes on degrade/merge).
- [ ] Never fabricate to fill a gap — null/empty is correct when the source
      doesn't state a value (enforced by extraction prompt + `hallucination_
      rate` in `ai/eval_harness.py`).
- [ ] Disputed events are always shown as disputed, never dropped from the
      public API (4-state confidence model, `CLAUDE.md`) — covered by a
      structural test in `tests/test_gates.py`.
- [ ] Tastemaker (human opinion) content never touches the event candidate/
      gating/promotion pipeline — separate trust category, always.
- [ ] No dynamic SQL; all DB queries parameterized (`tools/trust_gate.py`
      enforces no-dynamic-SQL mechanically).

## Dead code & deferred work (OPERATING_RULES §1)

- [ ] No stubs, no "TODO later," no dead/unreachable code paths. If a
      parameter, hook, or path can't actually fire in production, wire it or
      remove it — it isn't done either way.
- [ ] No `TODO`/`FIXME`/`XXX` markers left in shipped code
      (`tools/lint.py` flags these; if one is genuinely deferred work, it
      belongs in `TODOS.md`, not a code comment, with an owner and priority).
- [ ] Defects found in review are fixed in the same change, not deferred.
- [ ] No red tests — new work never lands on top of a failing test.

## Style & structure

- [ ] TypeScript strict mode everywhere in the Next.js app (`web/`). No `any`
      without a comment explaining why.
- [ ] Every API endpoint validates input (zod on the Next.js side, pydantic
      on the FastAPI side) before touching the DB.
- [ ] Auth checks required on every protected route (venue/creator claim
      actions, tastemaker posting, admin moderation).
- [ ] Module docstring required in every `worker/`, `ai/`, `api/`, `tools/`
      file (except `__init__.py`) — `tools/lint.py` enforces this
      mechanically; first ~7 lines should be a greppable summary for docs
      (this file follows that convention too).
- [ ] `print()` is not error handling in `worker/`/`api/` code — use logging
      (or re-raise); `tools/lint.py` flags `print()` calls used inside
      except-handlers or with error-hint string content.
- [ ] Comments explain *why*, not *what* (OPERATING_RULES §5).
- [ ] New tools/scripts: stdlib-first (no hard dependency on a package that
      might not be installed — mirrors why `tools/lint.py` doesn't hard-depend
      on `ruff`), `--help`-friendly argparse, loud specific exit codes (0
      clean / 1 violation / 2 hard failure — see `tools/README.md`).

## Tests

- [ ] Test behavior, not implementation; every test must be able to fail
      (no zero-assertion tests, no trivially-true assertions, no mocks
      asserted-on-but-never-invoked) — see `docs/TESTS.md` and
      `tools/test_audit.py`.
- [ ] Confidence-state and moderation-state transitions covered by a test in
      `tests/test_gates.py` (or the tastemaker-post equivalent) — `CLAUDE.md`
      review criterion #2.
- [ ] `dbintegration`/`perf`/`visual` tests marked and opt-in per
      `tests/conftest.py`'s convention — never invent an unregistered marker.

## Dependencies & scope

- [ ] New external dependency? Note it in STATE.md (`CLAUDE.md` review
      criterion #3) — this doc doesn't override that requirement, it just
      reminds reviewers to check for it.
- [ ] Touches the promotion pipeline or auth? Flag for a deeper review pass,
      not the fast default pass (`CLAUDE.md` review criterion #1).

---

**If you're a review persona:** your specific focus areas live in
`docs/review_personas/<your-name>.md`; this checklist is the shared baseline
every persona also checks, not a replacement for your specialized lens.
