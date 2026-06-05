# CurseBot — Changelog

## v2.5.0 — 2026-06-05

### Release Monitor — Volledige Detectie

**Nieuw**
- `bot/cogs/curseforge.py` v3.0.0 — volledig herbouwd
  - Detecteert updates voor ALLE addons: eigen addons én watchlist van alle guilds
  - `release_history` logging — persistente log van elke verstuurd embed
  - Multi-guild notificaties via `channel_config` per release type
  - WAF backoff: 403 detectie met 1m → 5m → 1u wachten
  - Eerste-registratie logica: geen spam bij herstart
  - `/check` force support via `STATS.force_check`
  - `_passes_filter()` — stable/beta/alpha/sb/all filter per watchlist item
- `bot/services/cache.py` v4 (DB_VERSION=4)
  - `release_history` tabel toegevoegd
  - `release_history_add()`, `release_history_get()`, `release_history_count()`
  - Automatische migratie v3→v4 bij startup

### UI — Header Patch Geïntegreerd

**Nieuw**
- `ui/app.py` v2.4.0 — volledig herschreven
  - Header met knoppen op één lijn via `pack(side="left")` — nooit meer verkeerde uitlijning
  - Alle 5 knoppen volledig geïmplementeerd: Stop, Cache, Herstart, Check, Update
  - Stop/Cache vragen bevestiging via modale dialog
  - Herstart doet stop → 2s wacht → start in aparte thread
  - Live poll loop via `after()` — thread-safe, elke seconde
  - Status indicator (●) live gekoppeld aan `STATS.bot_online`
  - Uptime timer in header
  - 6 stat-cards op dashboard: uptime, servers, addons, releases, watchlist, interval
  - Laatste/volgende check timing
  - Live logbox (laatste 30 regels) + volledig logboek tab
  - `gaming.tools` footer hyperlink
  - Modaal bevestigingsvenster voor destructieve acties

### Fixes & Infra

**Fix**
- `start_cursebot.bat` — Pillow herstart-loop opgelost
  - Pillow check *binnen* de `.venv` vóór loop start
  - Duidelijke foutmelding als `.venv` ontbreekt of beschadigd is
  - Toont Python versie bij elke start
- `requirements.txt` v2.5.0 — volledig: flask-cors, Pillow, keyring, python-dotenv toegevoegd
- `updater.py` v1.3.0 — MANAGED_FILES compleet
  - `ui/app.py`, `ui/setup_wizard.py`, `ui/__init__.py` toegevoegd
  - `bot/cogs/help.py`, `bot/services/key_manager.py` toegevoegd
  - `launch.py`, `FIX_PYTHON.bat` toegevoegd
  - Python versie check bij elke update run

**Nieuw**
- `FIX_PYTHON.bat` — herstel tool na Python versiewijziging
  - Verwijdert oude `.venv`, maakt nieuwe aan met huidige Python
  - Valideert Python 3.10+ vereiste
  - Verifieert Pillow na installatie
- `env.example` — toegevoegd aan repo (stond alleen lokaal)

---

## v2.3.0 — 2026-06-03

### Security & Setup

**Nieuw**
- `BotManager`: start/stop/restart bot zonder app sluiten
- Start knop in header (groen/rood wisselt met bot-state)
- Keyring security: API keys versleuteld via Windows Credential Manager
- Setup wizard bij eerste EXE start
- WAF backoff: Cloudfront 403 detectie, 60s→300s→3600s wachten
- PAT Bearer auth + Core key x-api-key auto-detectie
- `monitor_loop.error` handler: loop stopt niet meer bij fout
- `dashboard.py`: `p["id"]` AttributeError fix + `/api/stop` endpoint
- `key_manager.py`: OS keyring beveiliging voor API keys
- `setup_wizard.py`: eerste-start configuratie UI
- `icon.ico`: Slayer Alliance stijl, 6 Windows formaten
- `cursebot.spec`: keyring backends + alle bot modules compleet

---

## v2.1.0 — 2026-06-02

### Onboarding & Permissions

**Nieuw**
- Automatische onboarding bij guild join
- `/setup`, `/invite`, `/permissions` slash commands
- Bot stuurt test embed naar gekozen kanaal bij setup

---

## v2.0.0 — 2026-06-02

### Multi-channel · Statistieken · EXE Packaging

**Nieuw**
- Download statistieken per addon (SQLite)
- `/stats`, `/setchannel`, `/removechannel` slash commands
- Multi-channel notify per release type
- Native UI (CustomTkinter) volledig
- PyInstaller EXE packaging
