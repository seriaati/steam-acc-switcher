from __future__ import annotations

from typing import Any, Optional


def ci_lookup(mapping: dict[str, Any], key: str) -> Optional[str]:
    lk = key.lower()
    for existing in mapping:
        if existing.lower() == lk:
            return existing
    return None


def ci_get(mapping: dict[str, Any], key: str, default: Any = None) -> Any:
    actual = ci_lookup(mapping, key)
    return mapping[actual] if actual is not None else default


def ci_set(mapping: dict[str, Any], key: str, value: str) -> None:
    actual = ci_lookup(mapping, key)
    mapping[actual if actual is not None else key] = value
