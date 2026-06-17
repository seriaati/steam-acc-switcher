# steam-acc-switcher

A small CLI for switching between your saved Steam accounts on Linux, built with [`rich`](https://github.com/Textualize/rich) for a clean terminal UI.

It works the way Steam actually works on Linux: it edits the two plain-text VDF files Steam reads at startup to decide who to auto-login as. It doesn't touch passwords or 2FA.

## How it works

Steam picks its auto-login account from two files:

1. `<steam_root>/config/loginusers.vdf`, which has one block per account keyed by SteamID64. The active account is the one with `MostRecent` set to `"1"`.
2. `~/.steam/registry.vdf`, the Linux stand-in for the Windows registry. `AutoLoginUser` (an AccountName) under `Registry/HKCU/Software/Valve/Steam` is what Steam logs into.

A switch does four things: locate the files, cleanly shut Steam down, edit both files, then relaunch Steam.

Steam must be fully closed before writing, because it rewrites `loginusers.vdf` on exit and would clobber the change. The tool sends a clean `steam -shutdown` (not a kill), waits for the process to disappear, and aborts rather than risk corruption if Steam won't quit. Each file is backed up (`.bak`) and written atomically before being replaced.

It auto-detects native, Flatpak, and Snap installs.

## Prerequisite (one-time, per account)

You need to have logged into each account at least once with "Remember password" checked. That's what creates the saved-credential token (`ssfn*`) files this tool relies on. The switcher only flips which saved account is active. It never stores or types passwords or 2FA codes.

## Install

Requires Python 3.10+.

The easiest way is to install it as an isolated CLI tool, which puts `sas` and
`steam-acc-switcher` on your PATH:

```bash
# with uv (https://docs.astral.sh/uv/)
uv tool install steam-acc-switcher

# or with pipx
pipx install steam-acc-switcher
```

To install with plain `pip` instead:

```bash
pip install steam-acc-switcher
```

Or from a local checkout of this repo:

```bash
pip install .
```

## Usage

```bash
# Run with no arguments for the interactive picker. Your saved accounts are
# listed (active one starred), use ↑/↓ to move, Enter to switch, q to cancel.
sas

# Enrich the menu with online state / VAC status (public profile lookup).
sas --online

# Switch directly by AccountName or nickname (case-insensitive), skipping the menu.
sas alice

# Skip confirmation prompts.
sas alice --yes
```

In the interactive picker, press `r` to give the highlighted account a nickname
(blank to clear). Nicknames show up in the menu and can be used as switch targets,
e.g. `sas Main`.

`sas` and `steam-acc-switcher` are equivalent. You can also run it without installing via `python -m sas`.

Note: switching closes and reopens Steam, so save your game and exit any running game first.

## Notes

- VDF key casing varies between Steam versions (`mostrecent` vs `MostRecent`); keys are read and written case-insensitively, preserving existing casing.
- The `--online` enrichment uses Steam's public `https://steamcommunity.com/profiles/<id>?xml=1` endpoint, needs no auth, and fails gracefully when offline.
- Account state lives in Steam's own VDF files; the tool never touches credentials. The only thing it stores of its own is the optional nickname map, keyed by SteamID64, at `~/.config/sas/nicknames.json` (honoring `XDG_CONFIG_HOME`).
