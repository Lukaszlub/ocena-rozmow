from __future__ import annotations

import time
from pathlib import Path
from threading import Lock

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from src.core.config import AppConfig
from src.core.utils import safe_move
from src.pipelines.batch import process_file


class IncomingHandler(FileSystemEventHandler):
    def __init__(self, cfg: AppConfig, db_conn) -> None:
        self.cfg = cfg
        self.db_conn = db_conn
        self.lock = Lock()

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != ".mp3":
            return

        with self.lock:
            _wait_for_settle(path, int(self.cfg.watcher.get("settle_time_sec", 2)))
            process_file(path, self.cfg, self.db_conn)


def _wait_for_settle(path: Path, settle_time_sec: int) -> None:
    last_size = -1
    stable_for = 0
    while stable_for < settle_time_sec:
        if not path.exists():
            return
        size = path.stat().st_size
        if size == last_size:
            stable_for += 1
        else:
            stable_for = 0
            last_size = size
        time.sleep(1)


def run_watcher(cfg: AppConfig, db_conn) -> None:
    cfg.input_dir.mkdir(parents=True, exist_ok=True)

    event_handler = IncomingHandler(cfg, db_conn)
    observer = Observer()
    observer.schedule(event_handler, str(cfg.input_dir), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(int(cfg.watcher.get("idle_sleep_sec", 1)))
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
