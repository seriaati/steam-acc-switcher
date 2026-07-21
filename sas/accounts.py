from __future__ import annotations

import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import vdf

from sas.errors import SteamError
from sas.nicknames import load_nicknames
from sas.vdf_utils import ci_get, ci_lookup


@dataclass
class Account:
    steamid64: str
    account_name: str
    persona_name: str
    most_recent: bool
    timestamp: int = 0
    nickname: Optional[str] = None
    online_state: Optional[str] = None
    vac_banned: Optional[bool] = None


@dataclass
class LoginUsers:
    data: dict[str, Any]
    users_key: str
    accounts: list[Account] = field(default_factory=list)


def load_login_users(path: Path) -> LoginUsers:
    if not path.is_file():
        raise SteamError(
            f"No loginusers.vdf found at {path}.\n"
            "Log in to Steam at least once with 'Remember password' checked, "
            "then try again."
        )
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SteamError(f"Could not read {path}: {exc}") from exc

    if not raw_text.strip():
        raise SteamError(f"{path} is empty. No saved Steam accounts to switch between.")

    try:
        data = vdf.loads(raw_text)
    except Exception as exc:
        raise SteamError(f"{path} is corrupt or not valid VDF: {exc}") from exc

    users_key = ci_lookup(data, "users")
    users_block = data.get(users_key, {}) if users_key else {}
    if not isinstance(users_block, dict) or not users_block:
        raise SteamError(
            "No accounts found in loginusers.vdf. Log in to Steam once with "
            "'Remember password' checked first."
        )

    accounts: list[Account] = []
    for steamid64, block in users_block.items():
        if not isinstance(block, dict):
            continue
        accounts.append(
            Account(
                steamid64=str(steamid64),
                account_name=str(ci_get(block, "AccountName", "")),
                persona_name=str(ci_get(block, "PersonaName", "")),
                most_recent=str(ci_get(block, "MostRecent", "0")) == "1",
                timestamp=int(str(ci_get(block, "Timestamp", "0")) or 0),
            )
        )
    if not accounts:
        raise SteamError("No usable account entries found in loginusers.vdf.")

    nicks = load_nicknames()
    for acc in accounts:
        acc.nickname = nicks.get(acc.steamid64)

    return LoginUsers(data=data, users_key=users_key or "users", accounts=accounts)


def find_account(accounts: list[Account], name: str) -> Account:
    lname = name.lower()
    matches = [
        a
        for a in accounts
        if a.account_name.lower() == lname
        or (a.nickname and a.nickname.lower() == lname)
    ]
    if len(matches) == 1:
        return matches[0]
    options = ", ".join(sorted(a.account_name for a in accounts))
    if not matches:
        raise SteamError(f"Unknown account '{name}'. Known accounts: {options}")
    raise SteamError(f"'{name}' is ambiguous: multiple accounts match. Known: {options}")


def enrich_online(accounts: Iterable[Account], timeout: float = 4.0) -> None:
    for acc in accounts:
        url = f"https://steamcommunity.com/profiles/{acc.steamid64}?xml=1"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                root = ET.fromstring(resp.read())
        except (urllib.error.URLError, ET.ParseError, OSError):
            continue
        state = root.findtext("onlineState")
        if state:
            acc.online_state = state
        vac = root.findtext("vacBanned")
        if vac is not None:
            acc.vac_banned = vac == "1"
        persona = root.findtext("steamID")
        if persona and not acc.persona_name:
            acc.persona_name = persona
