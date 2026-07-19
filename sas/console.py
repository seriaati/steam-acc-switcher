from __future__ import annotations

from rich.console import Console

console = Console()
err_console = Console(stderr=True)

_verbose = False


def set_verbose(enabled: bool) -> None:
    global _verbose
    _verbose = enabled


def is_verbose() -> bool:
    return _verbose


def debug(message: str) -> None:
    if _verbose:
        err_console.print(f"debug: {message}", style="dim", markup=False, highlight=False)
