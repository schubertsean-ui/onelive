"""OneLive convergence model — SHADOW-ONLY substrate (C1).

Greppable summary: package for the data-convergence engine proposed in
docs/strategy/ONE_LIVE_CONVERGENCE_v1.md. Phase C1 ships the Subjective
Logic belief substrate (worker/convergence/sl.py) with ZERO coupling to the
live pipeline, ENFORCED both directions by tests/test_convergence_isolation.py
(inbound: no production module imports this package; outbound: every file
here imports stdlib/package-internal only; dynamic-import tokens banned) —
nothing here publishes, gates, or promotes. The count-based gate remains the
deciding gate until the founder ratifies each coupling per spec §11 (C5).
"""
