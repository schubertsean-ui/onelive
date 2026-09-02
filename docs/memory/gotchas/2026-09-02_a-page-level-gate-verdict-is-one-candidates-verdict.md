# A page's gate verdict is its FIRST candidate's verdict — never the page's

`worker/orchestrator.py::_process_fetched_page` extracts N candidates from a
page, then gates ONE of them: `candidate_id = outcome.candidate_ids[0]`. That
single verdict becomes `PageOutcome.decision` (`held` / `escalated` /
`ready_to_promote`) and everything downstream reads it as if it described the
page. The rest of the candidates are stamped later, by the backlog sweep, and
at the moment the loop is looking at them they may carry no verdict at all.

This is fine for what it was built for — the run report's terminal bucket — and
wrong for anything that acts per LISTING. A calendar of forty shows carries one
PASS that says nothing about the other thirty-nine, so a page-level PASS can
authorize a change to a row whose own evidence the gate would have escalated.

**The rule that came out of it (Session Contract #55):** treat a page-level
verdict as a PRECONDITION and never as a licence. Anything that acts on one
listing asks the gate about THAT listing —
`worker/listing_update.py::gate_passes_for` re-runs the same `evaluate_gate`
over the candidate's real stored extraction and evidence signals, and fails
closed (returns False) on any error.

**And do not read `event_candidate.status` instead.** It is a stamped value: it
can be stale, an ops action can have moved it, and for every candidate after
the first on a multi-event page it may never have been written. Re-compute.

Related: the same session found that `event.title` exists (migration 0010, not
0001) and that the two published-event readers disagree about which statuses
are visible (R-093) — both are the kind of thing worth checking against the
schema and the reader rather than assumed from a nearby file.
