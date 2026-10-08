"""Optional local environment loading for explicitly invoked maintenance scripts."""

import os
from pathlib import Path


LOCAL_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def load_local_env(path: Path = LOCAL_ENV_PATH) -> None:
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key.startswith("#") or key in os.environ:
                continue

            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            os.environ[key] = value
