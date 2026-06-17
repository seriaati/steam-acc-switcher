from __future__ import annotations

import os
import select
import sys
import termios
import tty
from typing import Optional

from rich import box
from rich.console import Group
from rich.live import Live
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from sas.accounts import Account
from sas.console import console
from sas.nicknames import save_nickname


def _ordered(accounts: list[Account]) -> list[Account]:
    return sorted(accounts, key=lambda a: (not a.most_recent, a.account_name.lower()))


def _menu(
    accounts: list[Account], selected: int, show_online: bool, running: bool, show_id: bool
) -> Group:
    show_header = show_online or show_id
    table = Table(box=None, pad_edge=False, show_header=show_header, header_style="dim")
    table.add_column(" ")
    table.add_column(" ")
    table.add_column("Account")
    table.add_column("Persona")
    if show_id:
        table.add_column("SteamID", style="dim")
    if show_online:
        table.add_column("Online")
        table.add_column("VAC")

    for idx, acc in enumerate(accounts):
        active = idx == selected
        pointer = Text("❯", style="bold cyan") if active else Text(" ")
        star = Text("★", style="green") if acc.most_recent else Text(" ")
        name_style = "bold cyan" if active else ("green" if acc.most_recent else "default")
        dim = "cyan" if active else "dim"
        name = Text(acc.account_name, style=name_style)
        if acc.nickname:
            name.append(f" ({acc.nickname})", style=dim)
        cells = [
            pointer,
            star,
            name,
            Text(acc.persona_name or "-", style=dim),
        ]
        if show_id:
            cells.append(Text(acc.steamid64, style=dim))
        if show_online:
            cells.append(Text(acc.online_state or "-", style=dim))
            if acc.vac_banned is None:
                cells.append(Text("-", style=dim))
            elif acc.vac_banned:
                cells.append(Text("BANNED", style="bold red"))
            else:
                cells.append(Text("clean", style=dim))
        table.add_row(*cells)

    dot = "[yellow]●[/] Steam is running" if running else "[dim]○ Steam is not running[/]"
    hint = "[dim]↑/↓/scroll move · ⏎ switch · r rename · i id · esc cancel[/]"
    return Group(
        Text("Select an account", style="bold"),
        Text(""),
        table,
        Text(""),
        console.render_str(f"{dot}   {hint}"),
    )


# Enable/disable SGR mouse tracking so the terminal reports scroll-wheel events.
_MOUSE_ON = "\x1b[?1000;1006h"
_MOUSE_OFF = "\x1b[?1000;1006l"


def _read_event(fd: int) -> str:
    """Read one logical key/mouse event from ``fd`` and normalize it to a token."""
    ch = os.read(fd, 1)
    if ch != b"\x1b":
        return ch.decode("utf-8", "replace")

    # A lone ESC is the prefix for arrow/mouse sequences. If no more bytes
    # arrive promptly, it was the user pressing Escape on its own.
    if not select.select([fd], [], [], 0.05)[0]:
        return "ESC"
    if os.read(fd, 1) != b"[":
        return "ESC"

    seq = b""
    while True:
        b = os.read(fd, 1)
        seq += b
        if b.isalpha() or b == b"~":
            break

    if seq.startswith(b"<"):  # SGR mouse: "<button;col;row" + 'M'/'m'
        button = seq[1:-1].split(b";", 1)[0]
        if button == b"64":
            return "UP"
        if button == b"65":
            return "DOWN"
        return ""
    return {b"A": "UP", b"B": "DOWN"}.get(seq, "")


def interactive_pick(
    accounts: list[Account], *, show_online: bool = False, running: bool = False
) -> Optional[Account]:
    ordered = _ordered(accounts)

    if not sys.stdin.isatty():
        return _numbered_pick(ordered)

    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    selected = 0
    try:
        # Each pass drives the live menu in raw mode; a "rename" request drops
        # back to cooked mode for a line prompt, then the loop re-enters.
        while True:
            outcome, selected = _menu_loop(fd, old_attr, ordered, selected, show_online, running)
            if outcome != "rename":
                return outcome
            _rename(ordered[selected])
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)


def _menu_loop(
    fd: int,
    old_attr: list,
    ordered: list[Account],
    selected: int,
    show_online: bool,
    running: bool,
):
    """Run the raw-mode menu until the user switches, cancels, or asks to rename.

    Returns ``(Account | None | "rename", selected)`` and always restores the
    terminal to ``old_attr`` (cooked mode) before returning.
    """
    console.file.write(_MOUSE_ON)
    console.file.flush()
    show_id = False
    try:
        tty.setcbreak(fd)
        with Live(_menu(ordered, selected, show_online, running, show_id), console=console, auto_refresh=False) as live:
            while True:
                try:
                    key = _read_event(fd)
                except KeyboardInterrupt:
                    return None, selected
                if key in ("UP", "k"):
                    selected = (selected - 1) % len(ordered)
                elif key in ("DOWN", "j"):
                    selected = (selected + 1) % len(ordered)
                elif key in ("\r", "\n"):
                    return ordered[selected], selected
                elif key == "ESC":
                    return None, selected
                elif key == "r":
                    return "rename", selected
                elif key == "i":
                    show_id = not show_id
                else:
                    continue
                live.update(_menu(ordered, selected, show_online, running, show_id), refresh=True)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)
        console.file.write(_MOUSE_OFF)
        console.file.flush()


def _rename(acc: Account) -> None:
    current = acc.nickname or ""
    shown = f" [dim](current: {current})[/]" if current else ""
    console.print(f"Nickname for [bold]{acc.account_name}[/]{shown} [dim](blank to clear):[/]")
    new = Prompt.ask("  nickname", default=current, show_default=False).strip()
    acc.nickname = new or None
    save_nickname(acc.steamid64, acc.nickname)


def _numbered_pick(ordered: list[Account]) -> Optional[Account]:
    table = Table(title="Pick an account to switch to", header_style="bold cyan")
    table.add_column("#", justify="right", style="bold")
    table.add_column("", width=2, justify="center")
    table.add_column("AccountName", style="bold")
    table.add_column("PersonaName")
    for idx, acc in enumerate(ordered, start=1):
        marker = Text("★", style="bold green") if acc.most_recent else Text(" ")
        name = acc.account_name + (f" ({acc.nickname})" if acc.nickname else "")
        table.add_row(str(idx), marker, name, acc.persona_name or "-")
    console.print(table)

    choice = IntPrompt.ask(
        "Select an account (0 to cancel)",
        choices=[str(i) for i in range(0, len(ordered) + 1)],
        show_choices=False,
    )
    return None if choice == 0 else ordered[choice - 1]
