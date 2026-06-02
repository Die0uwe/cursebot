# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — launch.py
Entry point voor PyInstaller .exe build.
Start bot + UI samen als één applicatie.
"""
import sys
import threading
import asyncio
from pathlib import Path

# Zorg dat de werkmap klopt bij .exe start
if getattr(sys, 'frozen', False):
    import os
    os.chdir(Path(sys.executable).parent)


def start_bot():
    """Bot + Flask dashboard in eigen thread."""
    import asyncio
    from bot.main import main
    asyncio.run(main())


def start_ui():
    """Native CustomTkinter UI."""
    import time
    time.sleep(2)  # Wacht even op bot startup
    from ui.app import main as ui_main
    ui_main()


if __name__ == "__main__":
    # Bot in achtergrond thread
    bot_thread = threading.Thread(target=start_bot, daemon=True, name="BotThread")
    bot_thread.start()

    # UI in hoofdthread (tkinter vereist main thread)
    start_ui()
