from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict


def setup_logging(cfg_logging: Dict[str, str]) -> None:
    if not cfg_logging or not cfg_logging.get("enabled", True):
        return

    level_name = str(cfg_logging.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    file_path = Path(cfg_logging.get("file_path", "logs/app.log"))
    file_path.parent.mkdir(parents=True, exist_ok=True)

    max_bytes = int(cfg_logging.get("max_bytes", 1_048_576))
    backup_count = int(cfg_logging.get("backup_count", 5))

    handler = RotatingFileHandler(
        file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
