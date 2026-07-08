"""Simple extraction-accuracy scorer for offline eval of the AI provider.
Source: extracted from Entertainment-App-Code-v1-4 reference build (ai/eval_harness.py)
"""


def evaluate_extraction(predicted: dict, expected: dict) -> float:
    if not expected:
        return 0.0
    score = 0
    total = len(expected)
    for k, v in expected.items():
        if predicted.get(k) == v:
            score += 1
    return score / max(1, total)
