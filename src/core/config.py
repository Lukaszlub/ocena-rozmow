from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any
import yaml


NAME_REGEX = re.compile(
    r"^[A-Za-zÀ-ÖØ-öø-ÿąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+ [A-Za-zÀ-ÖØ-öø-ÿąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+"
    r"([ _-].+)?\.mp3$"
)


@dataclass
class AppConfig:
    input_dir: Path
    invalid_dir: Path
    processed_dir: Path
    reports_dir: Path
    db_path: Path
    use_excel_export: bool
    weights: Dict[str, float]
    criteria: List[Dict[str, Any]]
    profanity_list: List[str]
    score_thresholds: Dict[str, float]
    transcription: Dict[str, str]
    scoring: Dict[str, str]
    watcher: Dict[str, str]
    logging: Dict[str, str]
    knowledge: Dict[str, str]


def load_config(path: Path) -> AppConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AppConfig(
        input_dir=Path(raw["input_dir"]),
        invalid_dir=Path(raw["invalid_dir"]),
        processed_dir=Path(raw["processed_dir"]),
        reports_dir=Path(raw["reports_dir"]),
        db_path=Path(raw["db_path"]),
        use_excel_export=bool(raw.get("use_excel_export", True)),
        criteria=raw.get("criteria", []),
        weights=_weights_from_criteria(raw),
        profanity_list=raw["profanity_list"],
        score_thresholds=raw["score_thresholds"],
        transcription=raw["transcription"],
        scoring=raw["scoring"],
        watcher=raw["watcher"],
        logging=raw.get("logging", {}),
        knowledge=raw.get("knowledge", {}),
    )


def is_valid_filename(name: str) -> bool:
    return bool(NAME_REGEX.match(name))


def parse_name_from_filename(name: str) -> tuple[str, str]:
    base = Path(name).stem
    parts = base.split(" – ")[0].strip().split(" ")
    if len(parts) < 2:
        return ("", "")
    return (parts[0], parts[1])


def _weights_from_criteria(raw: Dict[str, Any]) -> Dict[str, float]:
    if "criteria" in raw and raw["criteria"]:
        return {c["name"]: float(c["weight"]) for c in raw["criteria"]}
    return raw.get("weights", {})
