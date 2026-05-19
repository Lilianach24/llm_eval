"""Minimal dotenv loader used by this project (subset of python-dotenv API)."""
from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str = ".env", override: bool = False) -> bool:
    env_path = Path(path)
    if not env_path.exists():
        return False

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value
    return True
