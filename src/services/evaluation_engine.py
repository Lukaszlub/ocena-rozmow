from __future__ import annotations

from typing import Dict

from src.services.llm_scoring import score_transcript


def evaluate_transcript(transcript: str, cfg_scoring: Dict[str, str], weights: Dict[str, float]) -> Dict[str, float]:
    return score_transcript(transcript, cfg_scoring, weights)
