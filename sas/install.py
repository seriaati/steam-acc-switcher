from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sas.errors import SteamError

_ROOT_CANDIDATES: list[tuple[str, str]] = [
    ("~/.steam/steam", "native"),
    ("~/.local/share/Steam", "native"),
    ("~/.steam/root", "native"),
    ("~/.var/app/com.valvesoftware.Steam/.steam/steam", "flatpak"),
    ("~/.var/app/com.valvesoftware.Steam/.local/share/Steam", "flatpak"),
    ("~/snap/steam/common/.steam/steam", "snap"),
]

_REGISTRY_CANDIDATES: list[str] = [
    "~/.steam/registry.vdf",
    "~/.var/app/com.valvesoftware.Steam/.steam/registry.vdf",
    "~/snap/steam/common/.steam/registry.vdf",
]


@dataclass
class SteamInstall:
    root: Path
    loginusers: Path
    registry: Path
    kind: str

    @property
    def _base_cmd(self) -> list[str]:
        if self.kind == "flatpak":
            return ["flatpak", "run", "com.valvesoftware.Steam"]
        if self.kind == "snap":
            return ["snap", "run", "steam"]
        return ["steam"]

    @property
    def shutdown_cmd(self) -> list[str]:
        return self._base_cmd + ["-shutdown"]

    @property
    def launch_cmd(self) -> list[str]:
        return self._base_cmd


def detect_install() -> SteamInstall:
    root: Optional[Path] = None
    kind = "native"
    for raw, k in _ROOT_CANDIDATES:
        candidate = Path(raw).expanduser()
        if candidate.is_dir():
            root, kind = candidate, k
            break
    if root is None:
        raise SteamError(
            "Could not find a Steam installation. Looked for native, Flatpak "
            "and Snap installs in the usual locations."
        )

    registry: Optional[Path] = None
    for raw in _REGISTRY_CANDIDATES:
        candidate = Path(raw).expanduser()
        if candidate.is_file():
            registry = candidate
            break
    if registry is None:
        registry = Path("~/.steam/registry.vdf").expanduser()

    return SteamInstall(
        root=root,
        loginusers=root / "config" / "loginusers.vdf",
        registry=registry,
        kind=kind,
    )
