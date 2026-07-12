"""Thin re-export shim so callers can `from worker.multiconfirm import ...`
without depending on the fact that the gate logic itself lives in
worker/gating.py. Keep this file import-only — no logic belongs here.
"""
from worker.gating import multi_confirm_gate, GateResult

__all__ = ["multi_confirm_gate", "GateResult"]
