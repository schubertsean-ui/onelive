"""tools — operational scripts AND the shared routing policy module.

Greppable summary: this directory is a package so runtime code can import
`tools.model_router` — the invariant "the routing gate is enforced at the
entry point that actually runs" requires application code to consult the
SAME resolver the policy documents, not a duplicated local table that
drifts stale. Scripts here remain individually runnable
(`python tools/<name>.py`); see tools/README.md.
"""
