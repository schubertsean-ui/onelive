# A fragment read is NO read — never act on a document you have only partially read

Retrieval tokens: `skim`, `fragment`, `offset-limit`, `truncated-output`,
`partial-read`, `read-in-full`. Governing rule: `docs/OPERATING_RULES.md` → Rule Zero
(founder-directed 2026-08-02). Decision: `decisions/2026-08-02_complete-reading-gate.md`.

## The lesson

Reading a controlling document in fragments — an offset/limit slice, a truncated tool
result, the first page of many — and then acting on that fragment produces
confident-but-wrong actions. It happened twice in one session (a banned delay/timer;
a mis-stated trust invariant), both from acting on a partial read of the same docs.

## The rule of thumb (do this, every time)

- Before building/fixing/scanning/answering: read the controlling docs for the task
  IN FULL. If a file exceeds one read call, page through ALL of it first; do not act
  on the part you have seen.
- STATE.md is large — read the whole current Session Contract, not the first page.
- Prefer reading the full stable docs early: they cache, so completeness is cheap.
- "I got the gist" / "it looked like a one-liner" / "to save context" are the exact
  rationalizations that precede the failure. They are not permitted.

## How you know you skimmed

You cited a rule's effect without having read the rule's own text; you framed an
invariant from memory instead of from the doc; you acted before a full read was
confirmed. Any of these = STOP, read completely, then re-decide.
