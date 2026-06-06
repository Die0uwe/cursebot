# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — launch.py  v1.3.1

Entry point voor PyInstaller .exe build én directe start via start_cursebot.bat.
Start bot als daemon-thread, UI in de main thread.

WIJZIGINGEN v1.3.1:
  - CurseBotApp() zonder bot_manager arg (ui/app.py v2.4 interface fix)

WIJZIGINGEN v1.3.0:
  - _check_and_fix_packages(): runtime package check vóór alles
    Werkt zowel vanuit .exe (_internal/pip) als vanuit .venv
    Installeert stille ontbrekende packages zonder crash of herstart-loop
  - Splash console venster toont install-voortgang bij EXE start
  - Alle overige logica ongewijzigd

WIJZIGINGEN v1.2.0:
  - BotManager klasse: beheert bot-thread lifecycle (start / stop / restart)
  - UI kan bot herstarten via BotManager.start() zonder app te sluiten
  - Gedeeld BotManager-object beschikbaar via bot_manager module-global
  - Geen dubbele asyncio loops: elke start maakt een verse event loop
"""
import sys
import subprocess
import threading
import asyncio
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# ── Werkmap corrigeren bij .exe start ─────────────────────────────────────────
# PyInstaller frozen mode: sys.executable = pad naar CurseBot.exe
# We willen dat de werkmap de map IS waar de .exe staat (naast cache.db, .env)
if getattr(sys, "frozen", False):
    import os
    os.chdir(Path(sys.executable).parent)


# ══════════════════════════════════════════════════════════════════════════════
# PACKAGE CHECK — draait vóór alles, ook vóór tkinter import
# ══════════════════════════════════════════════════════════════════════════════

# Volledige lijst van wat CurseBot nodig heeft
# Formaat: (import_naam, pip_naam, minimale_versie_string)
_REQUIRED = [
    ("discord",        "discord.py>=2.4.0",          "discord.py"),
    ("httpx",          "httpx>=0.27.0",               "httpx"),
    ("pydantic",       "pydantic>=2.7.0",             "pydantic"),
    ("pydantic_settings", "pydantic-settings>=2.3.0", "pydantic-settings"),
    ("flask",          "flask>=3.0.0",                "flask"),
    ("flask_cors",     "flask-cors>=4.0.0",           "flask-cors"),
    ("customtkinter",  "customtkinter>=5.2.0",        "customtkinter"),
    ("pystray",        "pystray>=0.19.0",             "pystray"),
    ("PIL",            "Pillow>=10.0.0",              "Pillow"),
    ("keyring",        "keyring>=24.0.0",             "keyring"),
    ("dotenv",         "python-dotenv>=1.0.0",        "python-dotenv"),
]


def _check_and_fix_packages() -> bool:
    """
    Controleer alle vereiste packages. Installeer ontbrekende stil via pip.

    Werkt in drie contexten:
      1. Vanuit .venv  (start_cursebot.bat) — pip is in .venv/Scripts/pip
      2. Vanuit .exe   (PyInstaller frozen) — pip zit in _internal/
      3. Vanuit systeem Python              — pip is globaal beschikbaar

    Geeft True terug als alles OK is (ook na installatie).
    Geeft False terug als een kritiek package niet geïnstalleerd kon worden.
    """
    missing = []

    for import_name, pip_spec, label in _REQUIRED:
        try:
            __import__(import_name)
        except ImportError:
            missing.append((pip_spec, label))

    if not missing:
        return True  # alles aanwezig, snel pad

    # ── Bepaal het juiste pip-executable ──────────────────────────────────────
    if getattr(sys, "frozen", False):
        # EXE modus — pip zit naast de exe in _internal/
        exe_dir  = Path(sys.executable).parent
        pip_exec = exe_dir / "_internal" / "pip"
        if not pip_exec.exists():
            # Fallback: gebruik sys.executable zelf als -m pip
            pip_cmd = [sys.executable, "-m", "pip"]
        else:
            pip_cmd = [str(pip_exec)]
    else:
        # Script modus — gebruik dezelfde Python die nu draait
        pip_cmd = [sys.executable, "-m", "pip"]

    # ── Installeer elk missend package ────────────────────────────────────────
    failed = []
    for pip_spec, label in missing:
        print(f"[CurseBot] Ontbrekend: {label} — installeren...", flush=True)
        try:
            result = subprocess.run(
                pip_cmd + ["install", pip_spec, "--quiet", "--disable-pip-version-check"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                print(f"[CurseBot] ✓ {label} geïnstalleerd", flush=True)
            else:
                print(f"[CurseBot] ✗ {label} mislukt: {result.stderr.strip()[:120]}", flush=True)
                failed.append(label)
        except subprocess.TimeoutExpired:
            print(f"[CurseBot] ✗ {label} timeout na 120s", flush=True)
            failed.append(label)
        except Exception as e:
            print(f"[CurseBot] ✗ {label} fout: {e}", flush=True)
            failed.append(label)

    if failed:
        print(
            f"\n[CurseBot] WAARSCHUWING: {len(failed)} package(s) konden niet worden "
            f"geïnstalleerd: {', '.join(failed)}\n"
            f"           Sommige functies werken mogelijk niet.",
            flush=True,
        )
        # Alleen kritiek als discord of pydantic ontbreekt — de rest is degradable
        critical = {"discord.py", "pydantic", "pydantic-settings", "httpx"}
        if any(f in critical for f in failed):
            return False

    return True


# ── Voer package check uit vóór ALLE andere imports ───────────────────────────
# Dit is bewust buiten een if __name__ == "__main__" blok — ook bij import
# als module moet de check kunnen draaien (bijv. bij eerste EXE start).
_packages_ok = _check_and_fix_packages()

if not _packages_ok:
    print(
        "\n[CurseBot] FATAAL: Kritieke packages ontbreken en konden niet worden "
        "geïnstalleerd.\n"
        "           Draai FIX_PYTHON.bat of installeer handmatig:\n"
        "           pip install discord.py pydantic pydantic-settings httpx\n",
        flush=True,
    )
    # Wacht even zodat gebruiker het bericht kan lezen voor het venster sluit
    time.sleep(5)
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# BOTMANAGER
# ══════════════════════════════════════════════════════════════════════════════

class BotManager:
    """
    Beheert de lifecycle van de Discord bot-thread.

    De bot draait in een aparte daemon-thread met zijn eigen asyncio event loop.
    Een gestopte daemon-thread kan niet herstart worden in Python — BotManager
    lost dit op door bij elke start() een nieuwe thread + loop aan te maken.

    Gebruik:
        bot_manager.start()    # start of herstart de bot
        bot_manager.stop()     # stuur stop-signaal (netjes via STATS.stop_requested)
        bot_manager.is_running # property: True als bot-thread actief is
    """

    def __init__(self):
        self._thread:    threading.Thread | None = None
        self._lock       = threading.Lock()
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        """Geeft True als de bot-thread actief is en nog leeft."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """
        Start de bot in een nieuwe daemon-thread.
        Geeft True terug als succesvol gestart, False als al actief.
        """
        with self._lock:
            if self.is_running:
                log.warning("[BotManager] Bot draait al — start genegeerd")
                return False

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="BotThread",
            )
            self._thread.start()
            log.info("[BotManager] Bot-thread gestart")
            return True

    def stop(self) -> bool:
        """
        Stuur een stop-signaal naar de bot via STATS.stop_requested.
        Geeft True terug als signaal verstuurd, False als bot al gestopt is.
        """
        if not self.is_running:
            log.warning("[BotManager] Bot draait niet — stop genegeerd")
            return False

        try:
            from bot.services.stats import STATS
            STATS.stop_requested = True
            STATS.add_log("[BotManager] Stop aangevraagd")
            log.info("[BotManager] Stop-signaal verstuurd")
        except Exception as e:
            log.error(f"[BotManager] Stop-signaal mislukt: {e}")

        self._stop_event.set()
        return True

    def wait_until_stopped(self, timeout: float = 10.0):
        """Blokkeer tot bot gestopt is (max timeout seconden)."""
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self):
        """Interne thread-functie. Maakt een verse event loop per start."""
        try:
            from bot.main import main as bot_main

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(bot_main())
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                finally:
                    loop.close()

        except Exception as e:
            log.error(f"[BotManager] Bot-thread fout: {e}", exc_info=True)
        finally:
            log.info("[BotManager] Bot-thread gestopt")


# ── Module-global BotManager ──────────────────────────────────────────────────
# Gedeeld object — zowel launch.py als ui/app.py importeren dit
bot_manager = BotManager()


# ══════════════════════════════════════════════════════════════════════════════
# START FUNCTIES
# ══════════════════════════════════════════════════════════════════════════════

def start_ui():
    """
    Start de CustomTkinter UI in de main thread.
    Toont setup wizard als verplichte keys ontbreken.
    """
    import customtkinter as ctk

    # Migreer .env keys naar keyring bij eerste keer
    try:
        from bot.services.key_manager import migrate_from_env
        migrate_from_env()
    except Exception:
        pass

    from ui.app import CurseBotApp

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = CurseBotApp()
    app.mainloop()


if __name__ == "__main__":
    # Bot starten vóór UI — UI gebruikt bot_manager om status te tonen
    bot_manager.start()

    # UI in main thread (tkinter vereist main thread)
    start_ui()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : launch.py                                           ║
# ║  Role         : Core Entry Point                                    ║
# ║  Version      : 1.3.1                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-06                                          ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Runtime package check — nooit meer Pillow loop      ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
