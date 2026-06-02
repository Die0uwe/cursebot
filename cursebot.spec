# ==============================================================================
# CurseBot — PyInstaller spec bestand
# Gebruik: pyinstaller cursebot.spec
# Output: dist/CurseBot/CurseBot.exe
# ==============================================================================
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['launch.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('dashboard_static', 'dashboard_static'),
        ('ui/assets',        'ui/assets'),
        ('.env.example',     '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'tkinter',
        'tkinter.ttk',
        'PIL',
        'PIL.Image',
        'discord',
        'discord.ext.commands',
        'discord.ext.tasks',
        'flask',
        'httpx',
        'pydantic',
        'pydantic_settings',
        'bot.cogs.curseforge',
        'bot.cogs.admin',
        'bot.cogs.watchlist',
        'bot.services.curseforge_api',
        'bot.services.cache',
        'bot.services.stats',
        'bot.services.claude_api',
        'bot.utils.embeds',
        'bot.utils.logger',
        'bot.utils.retry',
        'bot.models.release',
        'ui.app',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy'],
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
    console=True,          # True = log venster zichtbaar (handig voor debug)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ui/assets/icon.ico',
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
