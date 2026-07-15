"""Extraction-precision golden-set harness (fail-closed).

The market analysis names extraction precision the venture's EXISTENTIAL risk
(a wrong "broken promise" verdict is defamation-adjacent), so the eval harness
exists before any extraction model does. This module scores an extractor's
output against hand-labeled examples and FAILS CLOSED:

- empty golden set -> error (a gate that cannot fail proves nothing);
- precision below the bar -> non-zero verdict;
- synthetic-only golden set -> the report SAYS SO, loudly, and refuses to
  bless thresholds (R-017: real EDGAR-sourced examples are required before
  any threshold is meaningful; this sandbox cannot reach sec.gov).

Scoring model (v0, deliberately strict):
- a predicted claim matches a labeled claim iff kind matches AND the labeled
  match_keys (metric/due_date/targets as applicable) match exactly;
- precision = matched_predictions / all_predictions,
  recall   = matched_labels / all_labels;
- per-kind breakdown is reported because precision on CAPABILITY_ASSERTION
  (the AI-washing class) can hide behind easy NUMERIC_GUIDANCE wins.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

GOLDEN_DIR = Path(__file__).resolve().parent / "golden_set"

# Release bar (v0 placeholder): meaningless until the golden set carries real
# examples (R-017). Kept here so the number is versioned and reviewed, not
# ambient. The bar may be RAISED without ceremony; lowering it is a gated,
# founder-visible change.
PRECISION_BAR = 0.98
RECALL_BAR = 0.80


class GoldenSetError(RuntimeError):
    pass


@dataclass(frozen=True)
class KindScore:
    kind: str
    labeled: int
    predicted: int
    matched: int

    @property
    def precision(self) -> float:
        return self.matched / self.predicted if self.predicted else 0.0

    @property
    def recall(self) -> float:
        return self.matched / self.labeled if self.labeled else 0.0


def load_examples(golden_dir: Path = GOLDEN_DIR) -> list[dict]:
    """Load labeled examples. Each example file is JSON:
    {"example_id", "synthetic": bool, "source_text", "labels": [claim dicts
    with a "match_keys" object]}."""
    files = sorted(golden_dir.glob("*.json"))
    if not files:
        raise GoldenSetError(f"golden set at {golden_dir} is EMPTY — an empty gate proves nothing")
    examples = []
    seen_ids = set()
    for f in files:
        ex = json.loads(f.read_text(encoding="utf-8"))
        missing = {"example_id", "synthetic", "source_text", "labels"} - set(ex)
        if missing:
            raise GoldenSetError(f"{f.name}: missing fields {sorted(missing)}")
        if not isinstance(ex["synthetic"], bool):
            raise GoldenSetError(f"{f.name}: 'synthetic' must be an explicit boolean — "
                                 "provenance of examples is never implicit")
        for label in ex["labels"]:
            # A label whose match_keys are all null (or empty) can be "matched"
            # by a vacuous prediction that names only the kind — that inflates
            # precision without extraction. Every label must carry at least one
            # discriminative (non-null) key; statement_substring is the
            # universal fallback for qualitative/capability claims.
            keys = label.get("match_keys", {})
            if not any(v not in (None, "") for v in keys.values()):
                raise GoldenSetError(
                    f"{f.name}: label of kind {label.get('kind')!r} has no discriminative "
                    "match key (all null/empty) — add e.g. statement_substring")
            ss = keys.get("statement_substring")
            if ss is not None and (not isinstance(ss, str) or not ss.strip()):
                raise GoldenSetError(
                    f"{f.name}: statement_substring must be a non-empty string when present")
        if ex["example_id"] in seen_ids:
            raise GoldenSetError(f"{f.name}: duplicate example_id {ex['example_id']!r} — "
                                 "prediction mapping would be ambiguous")
        seen_ids.add(ex["example_id"])
        examples.append(ex)
    return examples


def _keys_match(label: dict, prediction: dict) -> bool:
    if label["kind"] != prediction.get("kind"):
        return False
    matched_discriminative = False
    for key, want in label["match_keys"].items():
        if key == "statement_substring":
            statement = prediction.get("statement") or ""
            if not want or want.lower() not in statement.lower():
                return False
            matched_discriminative = True
            continue
        if prediction.get(key) != want:
            return False
        if want not in (None, ""):
            matched_discriminative = True
    # a match must rest on at least one non-null key — kind alone is vacuous
    return matched_discriminative


def score(examples: list[dict], predictions_by_example: dict[str, list[dict]]) -> dict:
    """Score predictions against labels. Returns a report dict; see verdict()."""
    per_kind: dict[str, dict] = {}
    for ex in examples:
        preds = list(predictions_by_example.get(ex["example_id"], []))
        used = [False] * len(preds)
        for label in ex["labels"]:
            k = per_kind.setdefault(label["kind"], {"labeled": 0, "predicted": 0, "matched": 0})
            k["labeled"] += 1
            for i, p in enumerate(preds):
                if not used[i] and _keys_match(label, p):
                    used[i] = True
                    k["matched"] += 1
                    break
        for p in preds:
            per_kind.setdefault(p.get("kind", "UNKNOWN"),
                                {"labeled": 0, "predicted": 0, "matched": 0})["predicted"] += 1
    kinds = [KindScore(kind=k, **v) for k, v in sorted(per_kind.items())]
    total_labeled = sum(k.labeled for k in kinds)
    total_predicted = sum(k.predicted for k in kinds)
    total_matched = sum(k.matched for k in kinds)
    return {
        "examples": len(examples),
        "synthetic_only": all(ex["synthetic"] for ex in examples),
        "kinds": kinds,
        "precision": total_matched / total_predicted if total_predicted else 0.0,
        "recall": total_matched / total_labeled if total_labeled else 0.0,
    }


def verdict(report: dict) -> tuple[bool, str]:
    """Fail-closed verdict. Synthetic-only golden sets can FAIL the gate but
    can never PASS it — passing requires real examples (R-017)."""
    lines = [f"golden-set: {report['examples']} examples, "
             f"precision={report['precision']:.3f} (bar {PRECISION_BAR}), "
             f"recall={report['recall']:.3f} (bar {RECALL_BAR})"]
    for k in report["kinds"]:
        lines.append(f"  {k.kind}: labeled={k.labeled} predicted={k.predicted} "
                     f"matched={k.matched} p={k.precision:.3f} r={k.recall:.3f}")
    ok = report["precision"] >= PRECISION_BAR and report["recall"] >= RECALL_BAR
    if report["synthetic_only"]:
        lines.append("SYNTHETIC-ONLY GOLDEN SET (R-017): mechanics exercised, thresholds "
                     "NOT meaningful — this gate cannot PASS until real EDGAR-sourced "
                     "examples are added.")
        ok = False
    lines.append("VERDICT: " + ("PASS" if ok else "FAIL (fail-closed)"))
    return ok, "\n".join(lines)
