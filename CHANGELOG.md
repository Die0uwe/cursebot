# CurseBot Changelog

## v2.3.0 — 2026-06-03

### Sprint 3C — Addon Thumbnails + Handleiding Redesign

**Nieuw**
- `Mijn addons` tab: addon logo thumbnails via PIL (48×48, zelfde als CF Browser)
- Downloads K/M formattering in addons tab (1.2K / 4.5M)
- Summary-regel per addon in addons tab
- Watch knop met toast-bevestiging in addons tab
- `CurseBot_Handleiding_v2.3.html`: volledig redesign
  - 40% korter — geen brede donkere vlakken
  - Compact hero met logo naast tekst
  - Sticky navigatiebalk
  - Feature cards 2-kolom grid
  - Screenshots hover-zoom + lightbox
  - Commands in tabel
  - Troubleshoot compact

---

## v2.2.2 — 2026-06-03

### Sprint 3B — Systeemvak + Logo in Header

**Nieuw**
- `LOGOSMALL.png` als logo in header (36×36, links van CurseBot tekst)
- Systeemvak (pystray): minimize → tray icoon verschijnt
  - Dubbelklik: venster herstellen
  - Rechtsklik menu: Openen · Bot starten/stoppen · Afsluiten
  - Graceful fallback als pystray niet beschikbaar
- `_on_unmap` event: minimize knop → automatisch naar tray
- `_quit_from_tray`: stopt bot netjes voor afsluiten
- `requirements.txt`: pystray>=0.19.0 toegevoegd
- `ui/assets/LOGOSMALL.png` toegevoegd aan repo

---

## v2.2.1 — 2026-06-03

### Sprint 3A — /help Command + Watchlist Count

**Nieuw**
- `/help` slash command: embedded overzicht alle 14 commands
  - Secties: Setup · Monitoring · Watchlist · Releases · Rechten
  - Publiek zichtbaar (geen admin), ephemeral
  - Bot avatar als embed thumbnail
- `bot/cogs/help.py`: nieuw bestand
- `BotStats.watchlist_count`: watchlist telt nu mee in dashboard
- Watchlist stat card toont echte count (was altijd "–")
- `curseforge.py`: watchlist_count bijwerken na elke discovery

---

## v2.2.0 — 2026-06-03

### Sprint 2 — CF Browser Direct API + Thumbnails + Log Kleuren

**Nieuw**
- CF Browser roept CF API direct aan (onafhankelijk van bot)
  - 3-laags fallback: CF direct → Flask API → project_list
- Addon cards in CF Browser: thumbnail via PIL, game version badge
- Downloads K/M formattering (1.2K / 4.5M)
- Live log kleurcoding: ERROR=rood · CF=goud · BOT=blauw · OK=groen

### Sprint 1 — UI Groter en Leesbaarder

**Nieuw**
- Venster 900×620 → 1100×700 (+22% breed)
- Alle fonts +1px (FONT_TITLE 13→14, FONT_BODY 12→13, FONT_SMALL 10→11)
- Sidebar 170px → 200px
- Stat card waarden Consolas 17→20px
- Live log hoogte 160→220px
- Nav knoppen height 34→38px

### Kern — CurseBot v2.2.0

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
