# tools/project_checks.d — the project's OWN gates

**This is where a project's domain physics get enforced.** The kernel ships
the runner, the review, the deferral scan, the Kaizen meter, and the model
routing — it deliberately does NOT ship your trust invariants, because it
cannot know them.

Drop an executable script here; `tools/validate` discovers and runs every
one, and its exit code is its verdict (0 = pass, non-zero = FAIL the whole
gate). Name them so the run reads clearly: `10_trust_invariants.sh`,
`20_schema_guard.sh`.

Rules, inherited from the kernel:
- **Fail closed.** Missing config, unreadable input, or "nothing to check"
  must be RED, never a quiet pass. A gate that cannot fail proves nothing.
- **Pin the defect shape.** Every check exists because something went wrong
  (or would); a test should demonstrate the check going red on that exact
  shape, or the check is unproven.
- **State the honest limit.** Say in the script's header what it does NOT
  catch. Overclaiming is the failure mode this whole model is built around.
- **Never loosen silently.** Making a check easier to pass is a founder
  decision (kernel I7).

If this directory is empty, `tools/validate` says so LOUDLY — an unguarded
project is a fact worth seeing, not a silent default.
