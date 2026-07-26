# FRICTION_LOG — pre-work adversarial attacks on plans

> **KERNEL DOC — project-agnostic, inherited verbatim.** The RULES and the ENTRY
> STRUCTURE below are kernel and never change; the ENTRIES are project data and
> start empty. Which actions count as irreversible for a given project, and who
> its attacker model is, are bound in `OVERLAY.md`. Text in `[square brackets]`
> is a placeholder the project must bind.

Greppable summary: append-only log of the Friction gate (charter, Agent org).
Before any irreversible action — **deploy, migration, spend, prompt-version
bump** — the plan is written HERE and attacked with: **"what breaks, who is
harmed, cheaper path, founder-crucial or not?"** Blockers must be answered in
writing, in this file, before the action executes. The attack MUST come from a
model outside the generator's family (kernel I3 write/grade separation applies
to planning too, not only to code review). This is pre-work, not paperwork: an
entry written after the action is not a friction entry, it is an incident
report.

## When an entry is MANDATORY

Any action that cannot be cheaply undone:

- **Deploy** — anything reaching [the trusted surface] or a live user.
- **Migration** — any schema, data, or state change that a `git revert` does
  not reverse.
- **Spend** — first spend on a new service, a raised cap, or the first
  scheduled/recurring run that spends per cycle.
- **Prompt-version bump** — any change to a prompt, model id, or decoding
  setting on a path that feeds [the trusted surface].
- **[project additions]** — anything the overlay's escalation section (kernel
  I7 additions) names as irreversible for this project.

Also mandatory before proposing any move on the overlay's adoption-step
declaration, and before any action a hat run flagged as one-way.

Not mandatory — and deliberately so, per cost discipline — for reversible work:
ordinary code, tests, docs, refactors. Ritual is not insight.

## Required structure (the six steps, in this order)

Each step is a distinct heading in the entry. Skipping one, or reordering the
last three, invalidates the entry.

1. **Frame — PRE-REGISTERED.** Write the question, the decision that will be
   made, and what evidence would change it, BEFORE any analysis. Pre-registration
   is what stops the frame from being retrofitted to the conclusion. (Blue hat —
   `docs/hats/blue.md`.)
2. **Facts pass.** What is actually known, separated from what is believed:
   numbers, current state, what the code/data says. Neutral only — no
   judgments, no recommendations in this section. (White hat — `docs/hats/white.md`.)
3. **Provocation battery.** Run the full battery per `docs/skills/po_provocation.md`
   (`tools/po_battery.py "<statement>"`) — all operators, standalone and in
   combination — and record the harvest: ideas kept, each traceable to the
   provocation that produced it. This is the OPENING move, before any attack:
   attacking first collapses the option space you were supposed to widen.
   Provocations are stimuli, never facts, and nothing here enters `docs/memory/`,
   any data record, or user-facing copy except by surviving the normal gates as
   an ordinary evidenced change. (Green hat — `docs/hats/green.md`.)
4. **Independent parallel lenses.** At least two lenses run on the same frame
   and facts, and **they never see each other's output** — independence is the
   whole value, and one lens summarizing another destroys it. **At least one
   must be a deliberate best-case lens** (Yellow — `docs/hats/yellow.md`): the
   harness is full of attackers, so the upside case needs a named owner or it
   never gets argued. Cross-family where keys allow. Record each lens's raw
   output verbatim, under its own sub-heading.
5. **Devil's-advocate attack on any consensus.** If the lenses agreed, that
   agreement is now the target: attack it explicitly. Unanimity among models is
   evidence of a shared blind spot at least as often as it is evidence of
   truth. This is also where the four standing questions get answered — what
   breaks, who is harmed, cheaper path, founder-crucial or not. (Black hat —
   `docs/hats/black.md`.)
6. **Merge that PRESERVES conflict.** The closing step never averages. Where
   the lenses disagreed, the merge states both positions and says which one the
   decision rides on and why — a merged entry from which you cannot reconstruct
   the disagreement is a defect, not a summary. (Blue hat again — the frame
   opens the run, the merge closes it.)

## Standing rules

- **Blockers are answered in writing, here, before the action runs.** An
  unanswered blocker is a stop, not a note. "Answered" means a written response
  in the entry, not a decision made in chat.
- **The attacker is outside the generator's family.** If that model is
  unavailable, the entry is marked **PROVISIONAL**, the reason is stated, and
  the action DOES NOT run on a provisional attack — it waits for a real one.
  A provisional entry must be re-attacked and updated in place, never quietly
  dropped.
- **No hat's output is evidence.** Friction output informs a decision; it never
  substitutes for a gate, and using it to argue a gate down is a
  gate-threshold relaxation: founder-crucial (kernel I7).
- **Append-only.** Entries are never deleted or rewritten to match the outcome.
  A plan that was attacked and then changed gets a follow-up entry (or an
  amendment section within the entry), so the diff stays auditable.
- **Founder-crucial po harvests land here.** Per `docs/skills/po_provocation.md`,
  a provocation run on a founder-crucial decision appends its harvest to the
  decision record or to the entry's step 3 above, so the Kaizen ledger can count
  po-sourced ideas that survived the gates (`docs/KAIZEN.md`, measure M6). The
  best-case lens's validated upside is counted the same way (M8).
- **Kaizen link.** Anything friction caught that a later gate would have missed
  is a ledger row (`docs/metrics/KAIZEN_LEDGER.md`, gate `friction`) with its
  class token — that is how this gate earns or loses its keep.

## Entry skeleton (copy for each new entry)

```markdown
## Entry #N — [YYYY-MM-DD] — [the irreversible action, in one line]

**Action class:** [deploy | migration | spend | prompt-version bump | other]
**Attacker model:** [id] ([outside generator family — yes/no])
**Status:** [ACTIVE | PROVISIONAL — reason | RESOLVED — action executed YYYY-MM-DD]

### 1. Frame (pre-registered [YYYY-MM-DD], before analysis)
- Question being decided:
- Decision this entry authorizes (or refuses):
- Evidence that would change the answer:

### 2. Facts
- [neutral, checkable statements only]

### 3. Provocation battery (harvest)
- Statement S:
- Kept ideas, each with its originating provocation:

### 4. Independent parallel lenses (blind to each other)
#### Lens A — [best-case / Yellow] — [model id]
[raw output]
#### Lens B — [lens name] — [model id]
[raw output]

### 5. Attack (including any consensus)
- What breaks:
- Who is harmed if this is wrong:
- Cheaper path:
- Founder-crucial or not:
- Attack on the lenses' consensus (if they agreed):

### 6. Merge (conflict preserved, not averaged)
- Where the lenses disagreed, and which side the decision rides on:
- Blockers raised, and the written answer to each:
- **Verdict:** [proceeds / does not proceed / proceeds subject to <named precondition>]
- **Ledger row:** [KAIZEN_LEDGER reference, or "none — nothing caught"]
```

---

## Entries

*(none yet — this project has taken no irreversible action. The first entry
goes below this line, newest last.)*
