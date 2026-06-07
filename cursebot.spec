# ==============================================================================
# CurseBot — PyInstaller spec bestand  v3.0.1
# Gebruik: pyinstaller cursebot.spec --clean --noconfirm
# Output: dist/CurseBot/CurseBot.exe
#
# Wijzigingen v3.0.1:
#   - bot.cogs.help toegevoegd (nieuw cog)
#   - bot.i18n.* toegevoegd (lokalisatie systeem)
#   - pystray toegevoegd (systeemvak tray icon)
#   - gaming_tools.webp + LOGOSMALL.png als data asset
#   - strings.json (i18n) als data asset
#   - beide env.example varianten (.env.example + env.example)
#   - _find_asset() zoekt ook naast .exe — correcte datas layout
#   - console=True voor debug build, False voor productie
# ==============================================================================
# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

# Bepaal welke assets bestaan (robuust voor ontbrekende bestanden)
datas = [
    ('dashboard_static',        'dashboard_static'),
    ('ui/assets',               'ui/assets'),
]

# Optionele root-assets (worden meegenomen als ze bestaan)
for optional in ['LOGOSMALL.png', 'gaming_tools.webp', 'gt2-1.webp',
                 'CURSEBOT.png', 'HEADER.png', 'icon.ico']:
    if Path(optional).exists():
        datas.append((optional, '.'))

# i18n strings
if Path('bot/i18n/strings.json').exists():
    datas.append(('bot/i18n/strings.json', 'bot/i18n'))

# images/ map (user assets)
if Path('images').exists():
    datas.append(('images', 'images'))

# env voorbeeld — check BEIDE varianten expliciet, voeg alleen toe als echt aanwezig
import os
for env_f in ['env.example', '.env.example']:
    if os.path.isfile(env_f) and os.path.getsize(env_f) > 0:
        datas.append((env_f, '.'))
        break  # maar één toevoegen

a = Analysis(
    ['launch.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # ── UI ────────────────────────────────────────────────────────────────
        'customtkinter',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.simpledialog',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL.ImageFilter',
        # ── Systeemvak ────────────────────────────────────────────────────────
        'pystray',
        'pystray._win32',
        # ── Discord ───────────────────────────────────────────────────────────
        'discord',
        'discord.ext.commands',
        'discord.ext.tasks',
        'discord.app_commands',
        'discord.ui',
        # ── Web / Flask ───────────────────────────────────────────────────────
        'flask',
        'flask_cors',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.routing',
        'werkzeug.exceptions',
        # ── HTTP ──────────────────────────────────────────────────────────────
        'httpx',
        'httpcore',
        'anyio',
        'anyio._backends._asyncio',
        'anyio._backends._trio',
        'h11',
        'certifi',
        # ── Pydantic ──────────────────────────────────────────────────────────
        'pydantic',
        'pydantic_settings',
        'pydantic.v1',
        'pydantic_core',
        # ── Security / keyring ────────────────────────────────────────────────
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
        'keyring.backends.SecretService',
        'keyring.backends.fail',
        'keyring.backends.null',
        'keyring.core',
        # ── Bot cogs ──────────────────────────────────────────────────────────
        'bot',
        'bot.cogs',
        'bot.cogs.curseforge',
        'bot.cogs.admin',
        'bot.cogs.watchlist',
        'bot.cogs.onboarding',
        'bot.cogs.help',          # nieuw v3.0
        # ── Bot services ──────────────────────────────────────────────────────
        'bot.services',
        'bot.services.curseforge_api',
        'bot.services.cache',
        'bot.services.stats',
        'bot.services.claude_api',
        'bot.services.key_manager',
        # ── Bot utils ─────────────────────────────────────────────────────────
        'bot.utils',
        'bot.utils.embeds',
        'bot.utils.logger',
        'bot.utils.retry',
        # ── Bot models ────────────────────────────────────────────────────────
        'bot.models',
        'bot.models.release',
        # ── i18n lokalisatie (nieuw v3.0) ─────────────────────────────────────
        'bot.i18n',
        'bot.i18n.translator',
        # ── UI modules ────────────────────────────────────────────────────────
        'ui',
        'ui.app',
        'ui.setup_wizard',
        # ── Overig ────────────────────────────────────────────────────────────
        'dotenv',
        'python_dotenv',
        'sqlite3',
        'asyncio',
        'threading',
        'webbrowser',
        'json',
        'urllib',
        'urllib.request',
        'urllib.parse',
        'io',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'IPython', 'jupyter', 'notebook',
        'test', 'tests', 'unittest',
        'PyQt5', 'PyQt6', 'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CurseBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # False = geen zwart venster, True = voor debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ui/assets/icon.ico',
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CurseBot',
)

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: cursebot.spec  │  v3.0.1  │  2026-06-07                    ║
# ║  Fix: bot.cogs.help + bot.i18n.* + pystray                        ║
# ║  Fix: gaming_tools.webp + LOGOSMALL.png als optionele datas       ║
# ║  Fix: images/ map meegenomen als aanwezig                          ║
# ║  Fix: strings.json (i18n) als data asset                           ║
# ║  Fix: anyio backends + pydantic_core + certifi hiddenimports       ║
# ║  Created by DieOuwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
