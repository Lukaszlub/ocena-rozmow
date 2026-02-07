from __future__ import annotations

import json
import os
import re
import time
from typing import Dict, Optional

from openai import OpenAI


SYSTEM_PROMPT = """
Jestes audytorem rozmow telefonicznych. Oceń rozmowe na podstawie transkrypcji.
Dla każdej kategorii podaj ocene w skali 0.0–1.0.
Kategorie: Otwarcie, Merytoryka, Proces, Jezyk, Domkniecie, Technika.
Wynik ma byc obiektywny i ostrozny. Jesli brak dowodu w transkrypcji, ocen nisko.
Zwroc tylko JSON zgodny ze schematem.
""".strip()


def _schema() -> Dict:
    return {
        "type": "object",
        "properties": {
            "scores": {
                "type": "object",
                "properties": {
                    "Otwarcie": {"type": "number"},
                    "Merytoryka": {"type": "number"},
                    "Proces": {"type": "number"},
                    "Jezyk": {"type": "number"},
                    "Domkniecie": {"type": "number"},
                    "Technika": {"type": "number"},
                },
                "required": [
                    "Otwarcie",
                    "Merytoryka",
                    "Proces",
                    "Jezyk",
                    "Domkniecie",
                    "Technika",
                ],
                "additionalProperties": False,
            }
        },
        "required": ["scores"],
        "additionalProperties": False,
    }


def _client_for_provider(cfg_scoring: Dict[str, str]) -> OpenAI:
    provider = (cfg_scoring.get("provider") or "openai").lower()
    if provider == "lmstudio":
        base_url = cfg_scoring.get("base_url") or "http://localhost:1234/v1"
        api_key = os.getenv("LM_STUDIO_API_KEY", "lmstudio")
        return OpenAI(base_url=base_url, api_key=api_key)
    return OpenAI()


def _extract_json(text: str) -> Optional[str]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return None


def score_transcript(transcript: str, cfg_scoring: Dict[str, str], weights: Dict[str, float]) -> Dict[str, float]:
    client = _client_for_provider(cfg_scoring)

    max_chars = int(cfg_scoring.get("max_transcript_chars", 20000))
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars]

    max_retries = int(cfg_scoring.get("max_retries", 2))
    retry_sleep = float(cfg_scoring.get("retry_sleep_sec", 1))
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            response = client.responses.create(
                model=cfg_scoring["model"],
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": SYSTEM_PROMPT,
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": transcript,
                            }
                        ],
                    },
                ],
                temperature=float(cfg_scoring.get("temperature", 0.0)),
                max_output_tokens=int(cfg_scoring.get("max_output_tokens", 400)),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "call_scoring",
                        "schema": _schema(),
                        "strict": True,
                    }
                },
            )

            raw = response.output_text
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                recovered = _extract_json(raw)
                if not recovered:
                    raise
                payload = json.loads(recovered)

            scores = payload["scores"]

            # Ensure all weights present in score output
            for k in weights.keys():
                scores.setdefault(k, 0.0)

            return scores
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(retry_sleep)
                continue
            break

    raise RuntimeError(f"LLM scoring failed after {max_retries + 1} attempts: {last_error}")
