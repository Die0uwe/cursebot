# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""CurseBot — updater.py  v1.5.0 — auto-updater via GitHub API.

CHANGES v1.5.0:
  - BOOTSTRAP STAP: updater.py update zichzelf EERST voor alles
    Als updater zichzelf heeft bijgewerkt -> exit 42 (herstart via bat)
    Zo draait altijd de nieuwste updater met de volledige MANAGED_FILES
  - FORCE_UPDATE set: kritieke interface-files worden ALTIJD gedownload
    ongeacht of ze lokaal al bestaan (oplost versie-mismatch crash)
  - bot/i18n/* toegevoegd aan MANAGED_FILES
  - dashboard_static/index.html toegevoegd

CHANGES v1.3.0:
  - MANAGED_FILES uitgebreid: help.py, key_manager.py, launch.py,
    ui/app.py, ui/setup_wizard.py, ui/__init__.py, FIX_PYTHON.bat
  - Python versie check: waarschuwing bij < 3.10
"""
import os, sys, json, shutil, hashlib, urllib.request, urllib.error
from pathlib import Path

REPO     = "Die0uwe/cursebot"
BRANCH   = "main"
API_BASE = f"https://api.github.com/repos/{REPO}"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

MANAGED_FILES = [
    "bot/__init__.py",
    "bot/main.py",
    "bot/config.py",
    "bot/cogs/__init__.py",
    "bot/cogs/admin.py",
    "bot/cogs/curseforge.py",
    "bot/cogs/help.py",
    "bot/cogs/onboarding.py",
    "bot/cogs/watchlist.py",
    "bot/models/__init__.py",
    "bot/models/release.py",
    "bot/services/__init__.py",
    "bot/services/cache.py",
    "bot/services/claude_api.py",
    "bot/services/curseforge_api.py",
    "bot/services/key_manager.py",
    "bot/services/stats.py",
    "bot/utils/__init__.py",
    "bot/utils/embeds.py",
    "bot/utils/logger.py",
    "bot/utils/retry.py",
    "bot/i18n/__init__.py",
    "bot/i18n/strings.json",
    "bot/i18n/translator.py",
    "ui/__init__.py",
    "ui/app.py",
    "ui/setup_wizard.py",
    "dashboard.py",
    "dashboard_static/index.html",
    "launch.py",
    "requirements.txt",
    "start_cursebot.bat",
    "FIX_PYTHON.bat",
    "updater.py",
    "ui/assets/LOGOSMALL.png",
    "ui/assets/gaming_tools.webp",
    "ui/assets/icon.ico",
]

# Bestanden die ALTIJD worden gedownload, ongeacht lokale versie.
# Dit voorkomt versie-mismatch crashes bij interface-wijzigingen.
FORCE_UPDATE = {
    "launch.py",
    "ui/app.py",
    "ui/setup_wizard.py",
    "ui/__init__.py",
    "bot/main.py",
    "bot/config.py",
    "updater.py",
}

NEVER_UPDATE = {".env", "cache.db", ".last_commit"}


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "CurseBot-Updater/1.5"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path):
    if not path.exists():
        return None
    return _sha256(path.read_bytes())


def _wipe_pycache(base_dir):
    count = 0
    for d in base_dir.rglob("__pycache__"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            count += 1
    return count


def _check_python():
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"[UPDATER] WAARSCHUWING: Python {v.major}.{v.minor} — vereist 3.10+")
        print("[UPDATER] Draai FIX_PYTHON.bat om dit op te lossen.")


def _bootstrap_self(base_dir, verbose=True):
    """
    Stap 0 — Bootstrap: updater.py zichzelf bijwerken VOOR alles.

    Als de lokale updater.py verouderd is (andere hash dan repo),
    wordt hij vervangen en geeft deze functie True terug.
    start_cursebot.bat herstart dan via exit 42.

    Dit garandeert dat altijd de nieuwste MANAGED_FILES-lijst actief is,
    inclusief launch.py en ui/app.py — zodat versie-mismatches onmogelijk worden.
    """
    def log(msg):
        if verbose:
            print(f"[UPDATER] {msg}", flush=True)

    try:
        remote_data = _get(f"{RAW_BASE}/updater.py")
    except Exception as e:
        log(f"Bootstrap check mislukt: {e}")
        return False

    local_path = base_dir / "updater.py"
    if _file_sha256(local_path) == _sha256(remote_data):
        return False  # Al up-to-date, geen herstart nodig

    log("Updater zelf is verouderd — bootstrap update uitvoeren...")
    try:
        local_path.write_bytes(remote_data)
        _wipe_pycache(base_dir)
        log("Bootstrap OK — herstart uitvoeren voor verse update-run.")
        return True  # Geef aan dat herstart gewenst is
    except Exception as e:
        log(f"Bootstrap schrijven mislukt: {e}")
        return False


def check_and_update(base_dir, verbose=True):
    def log(msg):
        if verbose:
            print(f"[UPDATER] {msg}", flush=True)

    _check_python()
    log("Update check gestart...")

    try:
        data       = json.loads(_get(f"{API_BASE}/commits/{BRANCH}?per_page=1"))
        remote_sha = data["sha"][:12]
    except Exception as e:
        log(f"GitHub niet bereikbaar: {e}")
        return False

    sha_file  = base_dir / ".last_commit"
    local_sha = sha_file.read_text().strip() if sha_file.exists() else ""

    if local_sha == remote_sha:
        log(f"Al up-to-date (commit {remote_sha}).")
        return False

    log(f"Nieuwe versie: {local_sha or 'onbekend'} → {remote_sha}")
    updated, failed = [], []

    for rel_path in MANAGED_FILES:
        if rel_path in NEVER_UPDATE:
            continue

        local_path = base_dir / Path(rel_path)
        force      = rel_path in FORCE_UPDATE

        # Sla over als bestand lokaal identiek is EN niet in FORCE_UPDATE
        if not force and local_path.exists():
            try:
                remote_data = _get(f"{RAW_BASE}/{rel_path}")
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    failed.append(rel_path)
                continue
            except Exception as e:
                log(f"  FOUT {rel_path}: {e}")
                failed.append(rel_path)
                continue

            if _file_sha256(local_path) == _sha256(remote_data):
                continue

            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(remote_data)
            log(f"  v {rel_path}")
            updated.append(rel_path)
            continue

        # FORCE_UPDATE of bestand ontbreekt — altijd downloaden
        try:
            remote_data = _get(f"{RAW_BASE}/{rel_path}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                failed.append(rel_path)
            continue
        except Exception as e:
            log(f"  FOUT {rel_path}: {e}")
            failed.append(rel_path)
            continue

        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Schrijf alleen als inhoud anders is (of force)
        if force or _file_sha256(local_path) != _sha256(remote_data):
            local_path.write_bytes(remote_data)
            tag = "[FORCE]" if force else ""
            log(f"  v {rel_path} {tag}")
            updated.append(rel_path)

    sha_file.write_text(remote_sha)

    if failed:
        log(f"  ! {len(failed)} bestand(en) mislukt: {', '.join(failed)}")

    if updated:
        wiped = _wipe_pycache(base_dir)
        log(f"  {wiped} __pycache__ map(pen) gewist")
        log(f"Update klaar — {len(updated)} bestand(en) bijgewerkt.")
        return True

    log("Geen bestandswijzigingen.")
    return False


if __name__ == "__main__":
    base = Path(__file__).parent

    # STAP 0: Bootstrap — updater zichzelf eerst bijwerken
    if _bootstrap_self(base):
        # Updater was verouderd en is vervangen — herstart zodat
        # de nieuwe versie (met volledige MANAGED_FILES) draait
        sys.exit(42)

    # STAP 1: Normale update-run
    changed = check_and_update(base)
    sys.exit(42 if changed else 0)

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: updater.py  │  v1.5.0  │  2026-06-06                       ║
# ║  Fix: bootstrap — updater.py update zichzelf EERST (exit 42)       ║
# ║  Fix: FORCE_UPDATE set — launch.py/ui/app.py altijd vers           ║
# ║  Add: bot/i18n/* aan MANAGED_FILES                                 ║
# ║  Created by DieOuwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
