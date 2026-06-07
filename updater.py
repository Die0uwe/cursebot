# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""CurseBot — updater.py  v1.7.0 — auto-updater via GitHub API.

CHANGES v1.7.0:
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
    "FIX_ALLES.bat",
    "FIX_ASSETS.bat",
    "HEALTH_CHECK.bat",
    "CURSEBOT_INSTALL_v2_5.bat",
    "BUILD_EXE.bat",
    "PUSH.bat",
    "start_cursebot_hidden.vbs",
    "LEES_MIJ.txt",
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

# Bestanden die NOOIT worden verwijderd, ook niet als ze niet in MANAGED_FILES staan.
# User-data, config, eigen bestanden blijven altijd intact.
NEVER_DELETE = {
    ".env",
    "cache.db",
    ".last_commit",
    ".bootstrapped",
    "cursebot.spec",        # eigen build config
    "env.example",
    ".env.example",
    "CHANGELOG.md",
    "README.md",
    "INSTALLATIE_WINDOWS.md",
    "licence",
    "Procfile",
    "railway.toml",
    "render.yaml",
    "find_author_id.py",
    "cursebot_setup.html",
    "cursebot_translation_editor.html",
}

# Mappen die volledig worden overgeslagen bij cleanup
# (nooit aanraken, ook al staat er niets in MANAGED_FILES)
NEVER_DELETE_DIRS = {
    ".venv",
    ".git",
    "logs",
    "images",
    "tests",
    "licence",
    "dashboard_static",  # eigen static files
}

# Extensies die door gebruiker geplaatst kunnen zijn — nooit verwijderen
SAFE_EXTENSIONS = {
    ".db", ".sqlite", ".sqlite3",   # databases
    ".env",                          # config
    ".log",                          # logs
    ".png", ".webp", ".ico",         # assets (user kan eigen toevoegen)
    ".jpg", ".jpeg", ".gif",
    ".pdf", ".html",                 # handleidingen
    ".zip", ".exe",                  # eigen builds
}


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "CurseBot-Updater/1.7"})
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


def cleanup_obsolete(base_dir, verbose=True):
    """
    Verwijder bestanden die niet meer in MANAGED_FILES staan.

    Logica:
    - Scan ALLEEN mappen die door de updater beheerd worden: bot/, ui/, root .py/.bat
    - Sla ALLES over dat in NEVER_DELETE of NEVER_DELETE_DIRS staat
    - Sla bestanden over met SAFE_EXTENSIONS (databases, afbeeldingen, logs etc.)
    - Vraag NOOIT iets te verwijderen zonder log — alles wordt gerapporteerd
    - Verwijder alleen als bestand NIET in MANAGED_FILES staat EN geen beschermde extensie heeft

    Geeft lijst terug van verwijderde bestanden.
    """
    def log(msg):
        if verbose:
            print(f"[UPDATER] {msg}", flush=True)

    # Bouw een set van alle bestanden die MOGEN bestaan
    allowed = set(MANAGED_FILES) | NEVER_DELETE

    # Welke root-bestanden controleren we?
    # Alleen .py, .bat, .vbs, .txt, .md in de root — geen willekeurige files
    MANAGED_EXTENSIONS_ROOT = {".py", ".bat", ".vbs", ".txt"}

    # Mappen die volledig door updater beheerd worden
    MANAGED_DIRS = {"bot", "ui"}

    removed = []

    # ── Scan root ─────────────────────────────────────────────────────────────
    try:
        for item in base_dir.iterdir():
            if item.is_dir():
                continue  # Mappen apart afhandelen
            rel = item.name

            # Nooit aanraken
            if rel in NEVER_DELETE:
                continue
            if item.suffix.lower() in SAFE_EXTENSIONS:
                continue
            if item.suffix.lower() not in MANAGED_EXTENSIONS_ROOT:
                continue  # Onbekende extensie in root — overslaan

            # Check of dit bestand in MANAGED_FILES staat
            if rel not in allowed:
                try:
                    item.unlink()
                    log(f"  🗑 Verouderd verwijderd: {rel}")
                    removed.append(rel)
                except Exception as e:
                    log(f"  ! Kon niet verwijderen {rel}: {e}")
    except Exception as e:
        log(f"  ! Root scan fout: {e}")

    # ── Scan bot/ en ui/ ──────────────────────────────────────────────────────
    for managed_dir in MANAGED_DIRS:
        dir_path = base_dir / managed_dir
        if not dir_path.exists():
            continue

        try:
            for item in dir_path.rglob("*"):
                if item.is_dir():
                    continue
                if "__pycache__" in item.parts:
                    continue

                rel = str(item.relative_to(base_dir)).replace("\\", "/")

                # Nooit aanraken
                if item.name in NEVER_DELETE:
                    continue
                if item.suffix.lower() in SAFE_EXTENSIONS:
                    continue

                # Check of in MANAGED_FILES
                if rel not in allowed:
                    try:
                        item.unlink()
                        log(f"  🗑 Verouderd verwijderd: {rel}")
                        removed.append(rel)
                    except Exception as e:
                        log(f"  ! Kon niet verwijderen {rel}: {e}")
        except Exception as e:
            log(f"  ! {managed_dir}/ scan fout: {e}")

    return removed


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

    # Zorg dat ui/assets/ map bestaat (ontbreekt na ZIP-install)
    (base_dir / "ui" / "assets").mkdir(parents=True, exist_ok=True)

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
# ║  File: updater.py  │  v1.7.0  │  2026-06-06                       ║
# ║  Fix: bootstrap — updater.py update zichzelf EERST (exit 42)       ║
# ║  Fix: FORCE_UPDATE set — launch.py/ui/app.py altijd vers           ║
# ║  Add: bot/i18n/* aan MANAGED_FILES                                 ║
# ║  Created by DieOuwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
