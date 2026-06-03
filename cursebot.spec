# ==============================================================================
# CurseBot — PyInstaller spec bestand  v2.2.0
# Gebruik: pyinstaller cursebot.spec --clean --noconfirm
# Output: dist/CurseBot/CurseBot.exe
# ==============================================================================
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['launch.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('dashboard_static',  'dashboard_static'),
        ('ui/assets',         'ui/assets'),
        ('.env.example',      '.'),
    ],
    hiddenimports=[
        # UI
        'customtkinter',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        # Discord
        'discord',
        'discord.ext.commands',
        'discord.ext.tasks',
        # Web
        'flask',
        'flask_cors',
        'werkzeug',
        'werkzeug.serving',
        # HTTP
        'httpx',
        'httpcore',
        'anyio',
        'h11',
        # Pydantic
        'pydantic',
        'pydantic_settings',
        'pydantic.v1',
        # Security — keyring backends
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
        'keyring.backends.SecretService',
        'keyring.backends.fail',
        'keyring.backends.null',
        # Bot modules
        'bot',
        'bot.cogs.curseforge',
        'bot.cogs.admin',
        'bot.cogs.watchlist',
        'bot.cogs.onboarding',
        'bot.services.curseforge_api',
        'bot.services.cache',
        'bot.services.stats',
        'bot.services.claude_api',
        'bot.services.key_manager',
        'bot.utils.embeds',
        'bot.utils.logger',
        'bot.utils.retry',
        'bot.models.release',
        # UI modules
        'ui.app',
        'ui.setup_wizard',
        # Overig
        'dotenv',
        'python_dotenv',
        'sqlite3',
        'asyncio',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'IPython', 'jupyter', 'notebook',
        'test', 'tests', 'unittest',
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
    console=False,         # False = geen console venster in productie
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
# ║  File: cursebot.spec │ v2.2.0 │ 2026-06-03                        ║
# ║  Fix: keyring backends, key_manager, setup_wizard, flask_cors      ║
# ║  Fix: console=False voor productie, alle bot.* modules compleet    ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
