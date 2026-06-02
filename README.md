# CurseBot — Slayer Alliance Edition

Automatische CurseForge release monitor voor alle addons van DieOuwe.
Stuurt Discord embeds bij elke nieuwe release, beta of alpha upload.

---

## Features

- 🔍 **Auto-discovery** — vindt automatisch alle addons van de auteur
- 🎨 **Slayer Alliance embeds** — kleurgecodeerd per release type
- 🤖 **AI changelogs** (optioneel) — Claude API vat changelogs samen
- 💾 **SQLite cache** — geen externe database nodig
- 🔄 **Retry logic** — exponential backoff bij API-fouten
- 🐳 **Docker-klaar** — één commando voor deployment

---

## Installatie (VPS / lokaal)

```bash
git clone <repo-url> cursebot
cd cursebot

python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Vul .env in met je tokens (zie hieronder)

python -m bot.main
```

---

## .env configuratie

| Variable | Verplicht | Omschrijving |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | Discord bot token |
| `RELEASE_CHANNEL_ID` | ✅ | Channel ID voor embeds |
| `CURSEFORGE_API_KEY` | ✅ | CurseForge API key |
| `CF_AUTHOR_SLUG` | ✅ | Jouw CF gebruikersnaam |
| `CHECK_INTERVAL_MINUTES` | ❌ | Standaard: 10 |
| `GUILD_ID` | ❌ | Voor dev: guild-specifieke slash sync |
| `ANTHROPIC_API_KEY` | ❌ | Voor AI changelog samenvatting |
| `SUMMARIZE_CHANGELOGS` | ❌ | `true` om AI samen te vatting aan te zetten |

---

## Discord bot aanmaken

1. Ga naar https://discord.com/developers/applications
2. New Application → Bot → Reset Token → kopieer token
3. OAuth2 → URL Generator → scopes: `bot`, `applications.commands`
4. Bot permissions: `Send Messages`, `Embed Links`, `View Channels`
5. Invite link gebruiken om bot toe te voegen aan server

---

## CurseForge API key

1. Ga naar https://console.curseforge.com/
2. API Keys → Create API Key
3. Kopieer de key naar `.env`
4. Trek eventueel een gecompromitteerde key in!

---

## Docker deployment

```bash
cd docker
docker-compose up -d

# Logs bekijken
docker-compose logs -f cursebot
```

---

## Slash commands

| Command | Omschrijving |
|---|---|
| `/status` | Monitor status + lijst van projecten |
| `/projects` | Alle getrackte addons met links |
| `/check` | Forceer onmiddellijke check |
| `/reset` | Wis cache (herdetectie van alle releases) |

> Alle commands zijn admin-only (vereisen `Administrator` permissie).

---

## Architectuur

```
bot/
├── main.py              Entry point
├── config.py            Settings via .env
├── cogs/
│   ├── curseforge.py    Monitor loop + release detectie
│   └── admin.py         Slash commands
├── services/
│   ├── curseforge_api.py  CF API client
│   ├── cache.py           SQLite cache
│   └── claude_api.py      AI changelog samenvatting
├── models/
│   └── release.py       Datamodellen
└── utils/
    ├── embeds.py        Discord embed builders
    ├── logger.py        Logging
    └── retry.py         Exponential backoff
```

---

*CurseBot · Slayer Alliance Edition · Midnight (12.0.5)*
