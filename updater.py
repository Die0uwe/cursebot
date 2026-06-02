# ==============================================================================
# Copyright (C) 2026  DieOuwe (https://www.dieouwe.nl / https://www.slayeralliance.com)
#
# This work is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# ==============================================================================
"""
CurseBot — updater.py
Auto-updater: checkt GitHub bij elke start op nieuwe versie.
Downloadt en overschrijft bestanden automatisch, dan herstart de bot.

Werkt via de GitHub API (geen git installatie nodig).
"""
import os
import sys
import json
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

REPO      = "Die0uwe/cursebot"
BRANCH    = "main"
API_BASE  = f"https://api.github.com/repos/{REPO}"
RAW_BASE  = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

# Bestanden die de updater beheert (relatief aan de bot root)
MANAGED_FILES = [
    "bot/__init__.py",
    "bot/main.py",
    "bot/config.py",
    "bot/cogs/__init__.py",
    "bot/cogs/admin.py",
    "bot/cogs/curseforge.py",
    "bot/models/__init__.py",
    "bot/models/release.py",
    "bot/services/__init__.py",
    "bot/services/cache.py",
    "bot/services/claude_api.py",
    "bot/services/curseforge_api.py",
    "bot/utils/__init__.py",
    "bot/utils/embeds.py",
    "bot/utils/logger.py",
    "bot/utils/retry.py",
    "requirements.txt",
    "updater.py",
]

# Bestanden die NOOIT overschreven worden (bevat secrets)
NEVER_UPDATE = {".env", "cache.db"}


def _get(url: str, timeout: int = 10) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "CurseBot-Updater/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return _sha256(path.read_bytes())


def check_and_update(base_dir: Path, verbose: bool = True) -> bool:
    """
    Checkt GitHub op updates en downloadt gewijzigde bestanden.
    Geeft True terug als er iets geüpdatet is (bot moet herstarten).
    """
    def log(msg: str):
        if verbose:
            print(f"[UPDATER] {msg}", flush=True)

    log("Update check gestart...")

    try:
        # Haal de laatste commit SHA op
        commit_data = json.loads(_get(f"{API_BASE}/commits/{BRANCH}?per_page=1"))
        remote_sha  = commit_data["sha"][:12]
    except Exception as e:
        log(f"Kan GitHub niet bereiken: {e} — sla update over.")
        return False

    # Check lokaal opgeslagen commit SHA
    sha_file  = base_dir / ".last_commit"
    local_sha = sha_file.read_text().strip() if sha_file.exists() else ""

    if local_sha == remote_sha:
        log(f"Al up-to-date (commit {remote_sha}).")
        return False

    log(f"Nieuwe versie gevonden: {local_sha or 'onbekend'} → {remote_sha}")

    updated   = []
    failed    = []

    for rel_path in MANAGED_FILES:
        if rel_path in NEVER_UPDATE:
            continue

        local_path = base_dir / Path(rel_path)

        try:
            remote_data = _get(f"{RAW_BASE}/{rel_path}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                log(f"  SKIP  {rel_path} (niet gevonden op GitHub)")
            else:
                log(f"  FOUT  {rel_path}: HTTP {e.code}")
                failed.append(rel_path)
            continue
        except Exception as e:
            log(f"  FOUT  {rel_path}: {e}")
            failed.append(rel_path)
            continue

        # Vergelijk SHA — alleen overschrijven als inhoud echt veranderd is
        if _file_sha256(local_path) == _sha256(remote_data):
            continue

        # Zorg dat de map bestaat
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Schrijf het nieuwe bestand
        local_path.write_bytes(remote_data)
        log(f"  ✓ bijgewerkt: {rel_path}")
        updated.append(rel_path)

    # Sla nieuwe commit SHA op
    sha_file.write_text(remote_sha)

    if updated:
        log(f"Update klaar — {len(updated)} bestand(en) bijgewerkt. Bot herstart...")
        return True
    else:
        log("Geen bestandswijzigingen (metadata-only commit).")
        return False


if __name__ == "__main__":
    base = Path(__file__).parent
    changed = check_and_update(base)
    sys.exit(0 if not changed else 42)  # exit 42 = herstart nodig

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : updater.py                                           ║
# ║  Role         : Util                                                 ║
# ║  Version      : 1.0.0                                                ║
# ║  Created      : 2026-06-02                                           ║
# ║  Last Updated : 2026-06-02  15:00                                    ║
# ║  Status       : New                                                  ║
# ║  Notes        : Auto-updater via GitHub API — geen git nodig         ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
