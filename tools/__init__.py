"""tools — operational scripts AND the shared routing policy module.

Greppable summary: made a package (2026-07-15, PR #21 evaluator round 1) so
runtime code can import `tools.model_router` — the trust invariant "the
routing gate is enforced at the entry point that actually runs" requires
`ai.claude_provider` to consult the SAME resolver the policy documents,
not a duplicated local table that drifts stale. Scripts here remain
individually runnable (`python tools/<name>.py`); see tools/README.md.
"""
