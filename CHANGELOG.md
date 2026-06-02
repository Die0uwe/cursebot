# CurseBot Changelog

## v2.1.0 — 2026-06-02

### Onboarding & Permissions

**Nieuw**
- Automatische onboarding bij guild join — kanaal kiezen via dropdown
- `/setup` — re-onboarding als de eerste setup gemist werd
- `/invite` — invite link met juiste permissions (integer: 67464256)
- `/permissions` — controleer rechten per kanaal
- Bot stuurt test embed naar gekozen kanaal bij setup
- Zoekt beste kanaal automatisch (system channel → general → eerste beschikbare)
- Correcte guild intents ingesteld (`intents.guilds=True`)
- Onboarding cog als eerste geladen zodat guild join altijd gepakt wordt
- UI sidebar: bot beheer sectie met invite en setup knoppen

---

## v2.0.0 — 2026-06-02

### Sprint 3 — Statistieken · Multi-channel · EXE Packaging

**Nieuw**
- Download statistieken bijhouden per addon (SQLite, per uur)
- `/stats` slash command — groei t.o.v. vorige meting
- `/setchannel` — aparte kanalen per release type (stable/beta/alpha/all)
- `/removechannel` — kanaalconfiguratie verwijderen
- Multi-channel notify: juiste kanaal per guild en release type
- Statistieken tab in native UI met progress bars
- PyInstaller `.exe` packaging (`BUILD_EXE.bat`)
- `launch.py` — single entry point voor bot + UI samen

**DB migratie**
- Schema v3: `download_stats` tabel + `channel_config` tabel
- Automatische migratie bij startup

---

## v1.1.0 — 2026-06-02

### Sprint 2 — Native CustomTkinter UI

**Nieuw**
- `ui/app.py` — 1100+ regels native Windows desktop applicatie
- Header: status indicator, uptime, actieknoppen
- Sidebar: navigatie + directe links (CurseForge, Discord, websites)
- Dashboard tab: 8 stat cards + live log
- Mijn addons tab: jouw CF projecten met + Watch knop
- Zoeken tab: zoekbalk + stable/beta/all filter + CF resultaten
- Watchlist tab: beheer met verwijder knoppen + bevestiging
- Instellingen tab: alle config velden
- Werkt ook zonder bot (offline modus)
- `start_cursebot.bat` opent UI automatisch naast bot

---

## v1.0.0 — 2026-06-02

### Sprint 1 — Watchlist systeem

**Nieuw**
- DB schema v2: `watchlist` + `addon_meta` tabellen
- `/watch` — addon toevoegen op naam, ID of auteur
- `/unwatch` — addon verwijderen op naam of ID
- `/watchlist` — overzicht per server
- `/search` — zoeken op CF, markeert wat al getrackt is
- Per-guild watchlist (max 50 addons)
- Release type filter per addon (all/stable/stable_beta)

---

## v0.1.0 — 2026-06-02

### Eerste release

**Features**
- CurseForge monitoring via `searchFilter` API
- Discord release embeds
- Auto-updater via GitHub API
- Flask web dashboard
- SQLite file cache
- Copyright headers + file cards op alle bestanden
