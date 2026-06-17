from __future__ import annotations

import argparse
import sys
from typing import Optional

from rich.panel import Panel

from sas.accounts import load_login_users
from sas.commands import run
from sas.console import err_console
from sas.errors import SteamError
from sas.install import detect_install


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sas",
        description="Switch between saved Steam accounts on Linux. "
        "Run with no arguments for an interactive picker.",
    )
    parser.add_argument(
        "account", nargs="?",
        help="AccountName to switch to. Omit to choose from an interactive menu.",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompts.",
    )
    parser.add_argument(
        "-o", "--online", action="store_true",
        help="Show online state / VAC status in the menu (needs network).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        install = detect_install()
        login = load_login_users(install.loginusers)
        run(install, login, args)
        return 0
    except SteamError as exc:
        err_console.print(
            Panel(str(exc), title="✖ Error", border_style="red", expand=False)
        )
        return 1
    except KeyboardInterrupt:
        err_console.print("\n[dim]Aborted.[/]")
        return 130


if __name__ == "__main__":
    sys.exit(main())
