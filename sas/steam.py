from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import vdf

from sas.accounts import Account, LoginUsers
from sas.console import console
from sas.errors import SteamError
from sas.install import SteamInstall
from sas.vdf_utils import ci_lookup, ci_set

SHUTDOWN_TIMEOUT_S = 30.0
SHUTDOWN_POLL_S = 0.5


def steam_is_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-x", "steam"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def shutdown_steam(install: SteamInstall) -> None:
    if not steam_is_running():
        return

    try:
        subprocess.run(
            install.shutdown_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise SteamError(
            f"Could not run '{install.shutdown_cmd[0]}' to shut Steam down. "
            "Is it on your PATH? Close Steam manually and retry."
        ) from exc

    deadline = time.monotonic() + SHUTDOWN_TIMEOUT_S
    with console.status("[bold yellow]Waiting for Steam to shut down…", spinner="dots"):
        while steam_is_running():
            if time.monotonic() >= deadline:
                raise SteamError(
                    f"Steam did not shut down within {SHUTDOWN_TIMEOUT_S:.0f}s. "
                    "Aborting without changes to avoid corrupting your config. "
                    "Close Steam manually and retry."
                )
            time.sleep(SHUTDOWN_POLL_S)


def launch_steam(install: SteamInstall) -> bool:
    try:
        subprocess.Popen(
            install.launch_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except FileNotFoundError:
        return False


def _atomic_write_vdf(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))

    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(vdf.dumps(data, pretty=True), encoding="utf-8")
    os.replace(tmp, path)


def write_login_users(install: SteamInstall, login: LoginUsers, target: Account) -> None:
    users_block = login.data[login.users_key]
    for steamid64, block in users_block.items():
        if not isinstance(block, dict):
            continue
        is_target = str(steamid64) == target.steamid64
        ci_set(block, "MostRecent", "1" if is_target else "0")
        if is_target:
            ci_set(block, "AllowAutoLogin", "1")
            ci_set(block, "RememberPassword", "1")
    _atomic_write_vdf(install.loginusers, login.data)


def write_registry(install: SteamInstall, target: Account) -> None:
    if install.registry.is_file():
        try:
            data = vdf.loads(install.registry.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SteamError(f"{install.registry} is corrupt: {exc}") from exc
    else:
        data = {}

    node = data
    for level in ("Registry", "HKCU", "Software", "Valve", "Steam"):
        actual = ci_lookup(node, level)
        if actual is None:
            node[level] = {}
            actual = level
        elif not isinstance(node[actual], dict):
            node[actual] = {}
        node = node[actual]

    ci_set(node, "AutoLoginUser", target.account_name)
    ci_set(node, "RememberPassword", "1")
    _atomic_write_vdf(install.registry, data)
