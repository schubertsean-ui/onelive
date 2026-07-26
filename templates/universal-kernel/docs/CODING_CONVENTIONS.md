# CODING_CONVENTIONS — reviewer-facing checklist

> **KERNEL DOC — project-agnostic, inherited verbatim.** This file describes the
> METHOD and nothing about any particular product. Language, framework, and
> module-path specifics belong in `OVERLAY.md`; the overlay may ADD checklist
> items but may never delete or weaken one here. Text in `[square brackets]` is a
> placeholder the overlay must bind.

Greppable summary: standalone checklist consolidating the coding rules
already stated in the project charter and `docs/OPERATING_RULES.md` §1/§3 into one
place reviewers/personas actually check against. This doc does not add new
rules — it does not override or contradict either source; if this doc and the
charter/OPERATING_RULES.md ever disagree, the latter two win and this doc
is stale and needs fixing.

Used by: `docs/review_personas/*.md` (each persona's checks map onto a subset
of this list) and [agent review tool] (prints the persona doc + diff for a
human/agent to review against this checklist).

## Trust & safety (highest priority — see OPERATING_RULES §0, §1, §3)

- [ ] No swallowed errors: `except: pass` / `except Exception: <blank>` (and the
      equivalent in every other language in the tree) is banned unless the caught
      branch is itself logged/audited with a comment justifying the swallow
      (`tools/lint.py` enforces this mechanically).
- [ ] Fail loudly on misconfiguration; only degrade safely on *transient*
      faults, and only with an audit/log line. Misconfiguration = missing key,
      unknown model id, absent extension, bad schema → raise. Transient =
      429/5xx/timeout → retry, then degrade WITH an audit row.
- [ ] The generative step never promotes/publishes directly — it only
      proposes candidates; reaching [trusted surface] always passes
      [promote gate], enforced by [project trust gate]'s never-publishes check.
- [ ] Every generation/degradation/heuristic-merge stage leaves an audit trail
      (provenance stamped on model output; audit-log writes on degrade/merge).
- [ ] Never fabricate to fill a gap — null/empty is correct when the source
      doesn't state a value (enforced by the prompt + [primary quality metric]
      in [eval harness]).
- [ ] Contested records are always disclosed as contested, never dropped from the
      public read path ([trust-state model]) — covered by a structural test in
      [gate test file].
- [ ] Content of a [separate trust category] never touches the verified-data
      candidate/gating/promotion pipeline — separate trust category, always.
- [ ] No dynamic SQL; all datastore queries parameterized ([project trust gate]
      enforces no-dynamic-SQL mechanically).

## Dead code & deferred work (OPERATING_RULES §1)

- [ ] No stubs, no "TODO later," no dead/unreachable code paths. If a
      parameter, hook, or path can't actually fire in production, wire it or
      remove it — it isn't done either way.
- [ ] No `TODO`/`FIXME`/`XXX` markers left in shipped code
      (`tools/lint.py` flags these; if one is genuinely deferred work, it
      belongs in TODOS.md, not a code comment, with an owner and priority —
      and if it is a deviation from the bar, it belongs in `docs/RECORD.md`).
- [ ] Defects found in review are fixed in the same change, not deferred.
- [ ] No red tests — new work never lands on top of a failing test.

## Style & structure

- [ ] Strict static typing everywhere the language offers it. No escape hatch
      (`any`, an unchecked cast, a blanket type-ignore) without a comment
      explaining why.
- [ ] Every API endpoint validates input against a declared schema
      ([schema validator]) before touching the datastore.
- [ ] Auth checks required on every protected route (any state-changing or
      privileged action — the project's list lives in `OVERLAY.md`).
- [ ] Module docstring/header required in every source file (except trivial
      package markers) — `tools/lint.py` enforces this mechanically; the first ~7 lines
      should be a greppable summary for docs (this file follows that convention
      too).
- [ ] `print()`/`console.log` is not error handling in service code — use logging
      (or re-raise); `tools/lint.py` flags print-family calls used inside
      except-handlers or with error-hint string content.
- [ ] Comments explain *why*, not *what* (OPERATING_RULES §5).
- [ ] New tools/scripts: stdlib-first (no hard dependency on a package that
      might not be installed), `--help`-friendly argument parsing, loud specific
      exit codes (0 clean / 1 violation / 2 hard failure).

## Tests

- [ ] Test behavior, not implementation; every test must be able to fail
      (no zero-assertion tests, no trivially-true assertions, no mocks
      asserted-on-but-never-invoked) — see `docs/TESTS.md` and `tools/test_audit.py`.
- [ ] [trust-state model] and moderation-state transitions covered by a test in
      [gate test file] (or the equivalent for each trust category).
- [ ] Opt-in test markers (integration / perf / visual) registered in the test
      config — never invent an unregistered marker.

## Dependencies & scope

- [ ] New external dependency? Note it in STATE.md — this doc doesn't override
      that requirement, it just reminds reviewers to check for it.
- [ ] Touches the promotion pipeline or auth? Flag for a deeper review pass,
      not the fast default pass.

---

**If you're a review persona:** your specific focus areas live in
`docs/review_personas/<your-name>.md`; this checklist is the shared baseline
every persona also checks, not a replacement for your specialized lens.
