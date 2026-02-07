from __future__ import annotations

from typing import Dict


def score_to_stars(score_total: float, thresholds: Dict[str, float]) -> int:
    if score_total >= thresholds["five_star"]:
        return 5
    if score_total >= thresholds["four_star"]:
        return 4
    if score_total >= thresholds["three_star"]:
        return 3
    return 1


def compute_score(weights: Dict[str, float], scores: Dict[str, float]) -> float:
    return sum(weights[k] * scores.get(k, 0.0) for k in weights.keys())
