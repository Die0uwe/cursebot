# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — launch.py  v1.2.0

Entry point voor PyInstaller .exe build en directe start via start_cursebot.bat.
Start bot als daemon-thread, UI in de main thread.

WIJZIGINGEN v1.2.0:
  - BotManager klasse: beheert bot-thread lifecycle (start / stop / restart)
  - UI kan bot herstarten via BotManager.start() zonder app te sluiten
  - Gedeeld BotManager-object beschikbaar via bot_manager module-global
  - Geen dubbele asyncio loops: elke start maakt een verse event loop
"""
import sys
import threading
import asyncio
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Werkmap corrigeren bij .exe start (PyInstaller frozen mode)
if getattr(sys, "frozen", False):
    import os
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
        """Geeft True als de bot-thread actief is en nog leeft."""
        return (
            self._thread is not None
            and self._thread.is_alive()
        )

    def start(self) -> bool:
        """
        Start de bot in een nieuwe daemon-thread.

        Geeft True terug als succesvol gestart, False als al actief.
        Thread-safe via lock.
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

        De bot pikt dit op via _stop_watcher in bot/main.py en sluit netjes af.
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

            # Verse event loop — verplicht na thread-herstart
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(bot_main())
            finally:
                try:
                    # Sluit alle pending tasks netjes af
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
# Gedeeld object — zowel launch.py als ui/app.py importeren dit
bot_manager = BotManager()


# ── Start functies ─────────────────────────────────────────────────────────────

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

    app = CurseBotApp(bot_manager=bot_manager)
    app.mainloop()


if __name__ == "__main__":
    # Bot starten vóór UI — UI gebruikt bot_manager om status te tonen
    bot_manager.start()

    # UI in main thread (tkinter vereist main thread)
    start_ui()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: launch.py │ v1.2.0 │ 2026-06-03                            ║
# ║  Add: BotManager klasse — start/stop/restart zonder app sluiten    ║
# ║  Add: bot_manager module-global gedeeld met ui/app.py              ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
