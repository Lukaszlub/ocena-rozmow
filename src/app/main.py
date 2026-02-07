from __future__ import annotations

import argparse
from pathlib import Path

from src.core.config import load_config
from src.core.logging_setup import setup_logging
from src.pipelines.batch import run_batch
from src.pipelines.watcher import run_watcher
from src.services.db import init_db
from src.app.gui import run_gui


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["batch", "watch", "gui"], default="watch")
    args = parser.parse_args()

    cfg = load_config(Path("config.yaml"))
    setup_logging(cfg.logging)
    db_conn = init_db(cfg.db_path)

    if args.mode == "batch":
        report = run_batch(cfg, db_conn)
        if report:
            print(f"Report: {report}")
        else:
            print("Batch complete (no Excel export).")
    elif args.mode == "watch":
        run_watcher(cfg, db_conn)
    else:
        run_gui(cfg, db_conn)


if __name__ == "__main__":
    main()
