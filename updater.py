# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — updater.py  v1.1.0
Auto-updater via GitHub API — geen git installatie nodig.
Fix: wist __pycache__ na update zodat Python niet de oude .pyc draait.
"""
import os
import sys
import json
import shutil
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

REPO      = "Die0uwe/cursebot"
BRANCH    = "main"
API_BASE  = f"https://api.github.com/repos/{REPO}"
RAW_BASE  = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

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
    "bot/services/stats.py",
    "bot/utils/__init__.py",
    "bot/utils/embeds.py",
    "bot/utils/logger.py",
    "bot/utils/retry.py",
    "dashboard.py",
    "dashboard_static/index.html",
    "requirements.txt",
    "updater.py",
]

NEVER_UPDATE = {".env", "cache.db", ".last_commit"}


def _get(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "CurseBot-Updater/1.1"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return _sha256(path.read_bytes())


def _wipe_pycache(base_dir: Path) -> int:
    """Verwijder alle __pycache__ mappen zodat Python niet de oude .pyc laadt."""
    count = 0
    for cache_dir in base_dir.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir, ignore_errors=True)
            count += 1
    return count


def check_and_update(base_dir: Path, verbose: bool = True) -> bool:
    def log(msg: str):
        if verbose:
            print(f"[UPDATER] {msg}", flush=True)

    log("Update check gestart...")

    try:
        commit_data = json.loads(
            _get(f"{API_BASE}/commits/{BRANCH}?per_page=1")
        )
        remote_sha = commit_data["sha"][:12]
    except Exception as e:
        log(f"Kan GitHub niet bereiken: {e} — sla update over.")
        return False

    sha_file  = base_dir / ".last_commit"
    local_sha = sha_file.read_text().strip() if sha_file.exists() else ""

    if local_sha == remote_sha:
        log(f"Al up-to-date (commit {remote_sha}).")
        return False

    log(f"Nieuwe versie: {local_sha or 'onbekend'} → {remote_sha}")

    updated = []
    failed  = []

    for rel_path in MANAGED_FILES:
        if rel_path in NEVER_UPDATE:
            continue

        local_path = base_dir / Path(rel_path)

        try:
            remote_data = _get(f"{RAW_BASE}/{rel_path}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                failed.append(rel_path)
            continue
        except Exception as e:
            log(f"  FOUT  {rel_path}: {e}")
            failed.append(rel_path)
            continue

        if _file_sha256(local_path) == _sha256(remote_data):
            continue

        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(remote_data)
        log(f"  ✓ {rel_path}")
        updated.append(rel_path)

    sha_file.write_text(remote_sha)

    if updated:
        # KRITIEK: wis __pycache__ zodat Python niet de oude .pyc draait
        wiped = _wipe_pycache(base_dir)
        log(f"  🗑 {wiped} __pycache__ map(pen) gewist")
        log(f"Update klaar — {len(updated)} bestand(en) bijgewerkt.")
        return True

    log("Geen bestandswijzigingen.")
    return False


if __name__ == "__main__":
    base    = Path(__file__).parent
    changed = check_and_update(base)
    sys.exit(42 if changed else 0)

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: updater.py │ v1.1.0 │ Updated │ 2026-06-02  16:45          ║
# ║  Fix: __pycache__ wissen na update — voorkomt stale bytecode       ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
