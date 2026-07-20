from __future__ import annotations

import argparse

from rich.panel import Panel
from rich.prompt import Confirm

from sas.accounts import Account, LoginUsers, enrich_online, find_account
from sas.console import console
from sas.install import SteamInstall
from sas.steam import (
    launch_steam,
    shutdown_steam,
    steam_is_running,
    watch_registry_autologin,
    write_login_users,
    write_registry,
)
from sas.ui import interactive_pick


def perform_switch(install: SteamInstall, login: LoginUsers, target: Account, *, assume_yes: bool) -> None:
    if target.most_recent and not assume_yes:
        if not Confirm.ask(
            f"[yellow]{target.account_name}[/] is already the active account. Re-apply anyway?",
            default=False,
        ):
            console.print("[dim]Nothing to do.[/]")
            return

    if not assume_yes:
        if not Confirm.ask(
            f"Switch to [bold cyan]{target.account_name}[/]? "
            "This will close and reopen Steam.",
            default=True,
        ):
            console.print("[dim]Cancelled.[/]")
            return

    shutdown_steam(install)
    write_login_users(install, login, target)
    write_registry(install, target)
    relaunched = launch_steam(install)

    persona = f" ({target.persona_name})" if target.persona_name else ""
    tail = (
        "Steam is relaunching, it will auto-login to this account."
        if relaunched
        else f"[yellow]Could not auto-launch '{install.launch_cmd[0]}'.[/] "
        "Start Steam yourself; it will log into this account."
    )
    console.print(
        Panel(
            f"Now logging in as [bold cyan]{target.account_name}[/]{persona}\n"
            f"[dim]{target.steamid64}[/]\n\n{tail}",
            title="✔ Switched account",
            border_style="green",
            expand=False,
        )
    )

    if relaunched:
        watch_registry_autologin(install)


def run(install: SteamInstall, login: LoginUsers, args: argparse.Namespace) -> None:
    if args.account:
        target = find_account(login.accounts, args.account)
    else:
        if args.online:
            with console.status("[cyan]Fetching profile info…", spinner="dots"):
                enrich_online(login.accounts)
        target = interactive_pick(
            login.accounts, show_online=args.online, running=steam_is_running()
        )
        if target is None:
            console.print("[dim]Cancelled.[/]")
            return
    perform_switch(install, login, target, assume_yes=args.yes)
