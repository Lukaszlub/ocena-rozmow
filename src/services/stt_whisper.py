from __future__ import annotations

from pathlib import Path
from typing import Dict

from openai import OpenAI

from src.core.models import TranscriptionResult


def transcribe(file_path: str, cfg_transcription: Dict[str, str]) -> TranscriptionResult:
    provider = (cfg_transcription.get("provider") or "openai").lower()
    if provider in {"faster_whisper", "local"}:
        return _transcribe_faster_whisper(file_path, cfg_transcription)
    return _transcribe_openai(file_path, cfg_transcription)


def _transcribe_openai(file_path: str, cfg_transcription: Dict[str, str]) -> TranscriptionResult:
    client = OpenAI()
    with Path(file_path).open("rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=cfg_transcription["model"],
            file=audio_file,
            response_format="text",
            language=cfg_transcription.get("language"),
            prompt=cfg_transcription.get("prompt") or None,
        )

    text = transcription.text if hasattr(transcription, "text") else str(transcription)

    return TranscriptionResult(
        file_name=Path(file_path).name,
        transcript=text,
        confidence=float(cfg_transcription.get("min_confidence", 0.85)),
        duration_sec=0,
    )


def _transcribe_faster_whisper(file_path: str, cfg_transcription: Dict[str, str]) -> TranscriptionResult:
    from faster_whisper import WhisperModel

    model_name = cfg_transcription.get("model", "base")
    device = cfg_transcription.get("device", "cpu")
    compute_type = cfg_transcription.get("compute_type", "int8")

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        file_path,
        language=cfg_transcription.get("language"),
        initial_prompt=cfg_transcription.get("prompt") or None,
    )

    text = "".join([seg.text for seg in segments]).strip()
    confidence = getattr(info, "language_probability", 0.0) or 0.0
    duration = int(getattr(info, "duration", 0.0) or 0.0)

    return TranscriptionResult(
        file_name=Path(file_path).name,
        transcript=text,
        confidence=confidence,
        duration_sec=duration,
    )
