from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


def _nick_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or "~/.config"
    return Path(base).expanduser() / "sas" / "nicknames.json"


def load_nicknames() -> dict[str, str]:
    """Return the {steamid64: nickname} map, or {} if missing/unreadable."""
    try:
        data = json.loads(_nick_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def save_nickname(steamid64: str, nickname: Optional[str]) -> None:
    """Set (or, when ``nickname`` is falsy, clear) the nickname for an account."""
    data = load_nicknames()
    if nickname:
        data[steamid64] = nickname
    else:
        data.pop(steamid64, None)
    path = _nick_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
