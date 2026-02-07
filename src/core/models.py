from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class TranscriptionResult:
    file_name: str
    transcript: str
    confidence: float
    duration_sec: int


@dataclass
class EvaluationResult:
    first_name: str
    last_name: str
    file_name: str
    evaluation_timestamp: datetime
    transcript: str
    score_total: float
    stars: int
    profanity_flag: bool
    profanity_phrases: List[str]
    profanity_excerpt: str
    score_breakdown: Dict[str, float]
    evidence_breakdown: Dict[str, str]
    evidence_summary: str
    transcription_confidence: float
    call_duration_sec: int
    file_hash: str
