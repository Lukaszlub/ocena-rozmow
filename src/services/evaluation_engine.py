from __future__ import annotations

from typing import Dict

from src.services.llm_scoring import score_transcript


def evaluate_transcript(
    transcript: str, cfg_scoring: Dict[str, str], criteria: list[dict], knowledge_ctx: list[str]
) -> tuple[Dict[str, float], Dict[str, str]]:
    return score_transcript(transcript, cfg_scoring, criteria, knowledge_ctx)
