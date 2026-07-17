"""PURE DATA: the golden-set exam's release-blocking thresholds.

Must stay a pure data module — docstring + constant assignments only
(tools/pure_data.py contract). Split out of the runner (evaluator r13
nit) so the secretless evidence verifier can import the thresholds
without referencing the exam runner module at all, keeping the
trust_gate exam-channel confinement allowlist minimal. Threshold
CHANGES here are gate-custody + threshold territory: evaluator-mandatory
and, for any loosening, founder-crucial (charter).
"""

HALLUCINATION_MAX = 0.01   # founder-ratified 2026-07-15 ("BEGIN at 1%"); one-way ratchet
RECALL_MIN = 0.80          # anti-gaming floor (going mute is not safety); ratchetable
SAMPLE_FLOOR = 300         # both floors: set must CARRY >=300 facts; a PASS asserts >=300

# Installed packages whose versions shape exam behavior (evaluator r24):
# the API client (request/response semantics, retry/normalization
# surface) and the schema validator. The runner records their installed
# versions in the report; the evidence verifier requires those to equal
# the exact '=='-pins in worker/requirements.txt (whose bytes are also
# inside the harness manifest hash), so evidence minted under one
# dependency set can never certify a PR under another.
EXAM_PACKAGES = ("anthropic", "pydantic")
