# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — launch.py  v1.2.1

Entry point voor PyInstaller .exe build en directe start via start_cursebot.bat.
Start bot als daemon-thread, UI in de main thread.

WIJZIGINGEN v1.2.1:
  - Auto-installer: ontbrekende packages worden automatisch geïnstalleerd
  - Crash loop fix: ImportError stopt de restart loop, installeert en herstart
  - customtkinter, Pillow, aiohttp, requests gecontroleerd bij elke start
"""
import sys
import subprocess
import os

# ── AUTO-INSTALLER (voor alle andere imports) ──────────────────────────────────
# Vereiste packages — worden automatisch geïnstalleerd als ze ontbreken
REQUIRED_PACKAGES = {
    "customtkinter": "customtkinter",
    "PIL":           "Pillow",
    "aiohttp":       "aiohttp",
    "requests":      "requests",
}

def _ensure_packages():
    missing = []
    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append((import_name, pip_name))

    if not missing:
        return True  # Alles OK

    print("\n" + "="*50)
    print("  CurseBot — Ontbrekende packages gevonden")
    print("="*50)
    for imp, pip in missing:
        print(f"  Ontbreekt: {imp}  (pip install {pip})")
    print()

    all_ok = True
    for imp, pip in missing:
        print(f"  [INSTALL] {pip}...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pip, "--quiet", "--no-warn-script-location"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✓")
        else:
            print(f"✗ MISLUKT")
            print(f"    Fout: {result.stderr.strip()[:200]}")
            all_ok = False

    if all_ok:
        print("\n  [OK] Alle packages geïnstalleerd — herstart...")
        print("="*50 + "\n")
        # Herstart hetzelfde script — packages zijn nu beschikbaar
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        print("\n  [FOUT] Installatie mislukt.")
        print("  Oplossing: open Command Prompt en typ:")
        print(f"    pip install {' '.join(p for _, p in missing)}")
        print("="*50)
        input("\n  Druk ENTER om te sluiten...")
        sys.exit(1)

_ensure_packages()
# ── EINDE AUTO-INSTALLER ───────────────────────────────────────────────────────

import threading
import asyncio
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Werkmap corrigeren bij .exe start (PyInstaller frozen mode)
if getattr(sys, "frozen", False):
    os.chdir(Path(sys.executable).parent)


# ── BotManager ─────────────────────────────────────────────────────────────────

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
        self._thread:      threading.Thread | None = None
        self._lock         = threading.Lock()
        self._stop_event   = threading.Event()

    @property
    def is_running(self) -> bool:
        return (
            self._thread is not None
            and self._thread.is_alive()
        )

    def start(self) -> bool:
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
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self):
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


# ── Module-global BotManager ───────────────────────────────────────────────────
bot_manager = BotManager()


# ── Start functies ─────────────────────────────────────────────────────────────

def start_ui():
    """
    Start de CustomTkinter UI in de main thread.
    Packages zijn gegarandeerd aanwezig dankzij _ensure_packages() bovenaan.
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

    app = CurseBotApp(bot_manager=bot_manager)
    app.mainloop()


if __name__ == "__main__":
    bot_manager.start()
    start_ui()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: launch.py │ v1.2.1 │ 2026-06-05                            ║
# ║  Fix: auto-installer voor ontbrekende packages (customtkinter etc) ║
# ║  Fix: crash loop gestopt — ImportError nu netjes afgehandeld       ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
