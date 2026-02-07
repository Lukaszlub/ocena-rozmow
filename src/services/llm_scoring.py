from __future__ import annotations

import json
import os
import re
import time
from typing import Dict, Optional

from openai import OpenAI


SYSTEM_PROMPT = """
Jestes audytorem rozmow telefonicznych. Ocen rozmowe na podstawie transkrypcji.
Dla kazdej kategorii podaj ocene w skali 0.0-1.0.
Kategorie: Otwarcie, Merytoryka, Proces, Jezyk, Domkniecie, Technika.
Wynik ma byc obiektywny i ostrozny. Jesli brak dowodu w transkrypcji, ocen nisko.
Zwroc JSON:
{
  "scores": { "Kryterium": 0.0-1.0, ... },
  "evidence": { "Kryterium": "krotki cytat z transkrypcji" }
}
Jesli brak dowodu, evidence ustaw na pusty string.
Evidence musi byc doslownym cytatem z transkrypcji (krotki fragment).
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


def _normalize_scores(payload: Dict, criteria: list[dict]) -> Dict[str, float]:
    names = [c["name"] for c in criteria]
    if "scores" in payload and isinstance(payload["scores"], dict):
        scores = payload["scores"]
    else:
        scores = {k: payload.get(k, 0.0) for k in names if k in payload}
        if not scores:
            raise KeyError("scores")
    for k in names:
        scores.setdefault(k, 0.0)
    return scores


def _normalize_evidence(payload: Dict, criteria: list[dict]) -> Dict[str, str]:
    names = [c["name"] for c in criteria]
    ev = payload.get("evidence", {}) if isinstance(payload.get("evidence", {}), dict) else {}
    if not ev:
        ev = {k: "" for k in names}
    for k in names:
        ev.setdefault(k, "")
    return ev


def score_transcript(
    transcript: str, cfg_scoring: Dict[str, str], criteria: list[dict], knowledge_ctx: list[str]
) -> tuple[Dict[str, float], Dict[str, str]]:
    client = _client_for_provider(cfg_scoring)
    provider = (cfg_scoring.get("provider") or "openai").lower()

    max_chars = int(cfg_scoring.get("max_transcript_chars", 20000))
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars]

    max_retries = int(cfg_scoring.get("max_retries", 2))
    retry_sleep = float(cfg_scoring.get("retry_sleep_sec", 1))
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            criteria_txt = "\n".join(
                [f"- {c['name']}: {c.get('description','')}".strip() for c in criteria]
            )
            knowledge_txt = "\n".join(knowledge_ctx) if knowledge_ctx else ""

            sys_prompt = SYSTEM_PROMPT + "\nKryteria:\n" + criteria_txt
            if knowledge_txt:
                sys_prompt += "\n\nBaza wiedzy (uzyj do weryfikacji prawdy):\n" + knowledge_txt

            if provider == "lmstudio":
                response = client.chat.completions.create(
                    model=cfg_scoring["model"],
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": transcript},
                    ],
                    temperature=float(cfg_scoring.get("temperature", 0.0)),
                    max_tokens=int(cfg_scoring.get("max_output_tokens", 400)),
                )
                raw = response.choices[0].message.content or ""
            else:
                response = client.responses.create(
                    model=cfg_scoring["model"],
                    input=[
                        {
                            "role": "system",
                            "content": [
                                {"type": "input_text", "text": sys_prompt},
                            ],
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": transcript},
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

            scores = _normalize_scores(payload, criteria)
            evidence = _normalize_evidence(payload, criteria)
            return scores, evidence
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(retry_sleep)
                continue
            break

    raise RuntimeError(f"LLM scoring failed after {max_retries + 1} attempts: {last_error}")
