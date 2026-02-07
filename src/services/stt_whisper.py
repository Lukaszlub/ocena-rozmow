from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from src.core.models import TranscriptionResult


def transcribe(file_path: str, cfg_transcription: dict) -> TranscriptionResult:
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

    # Confidence/duration are not always returned; keep best-effort placeholders.
    return TranscriptionResult(
        file_name=Path(file_path).name,
        transcript=text,
        confidence=float(cfg_transcription.get("min_confidence", 0.85)),
        duration_sec=0,
    )
