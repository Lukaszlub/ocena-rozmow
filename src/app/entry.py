from __future__ import annotations

import os
import sys
from pathlib import Path

from src.app.main import main


def _ensure_cwd_to_exe() -> None:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        os.chdir(exe_dir)


if __name__ == "__main__":
    _ensure_cwd_to_exe()
    sys.argv = [sys.argv[0], "--mode", "gui"]
    main()
