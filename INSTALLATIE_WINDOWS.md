# CurseBot — Windows Installatie

## Wat je nodig hebt
- Python 3.12 (van python.org — vink "Add to PATH" aan bij installatie)
- De cursebot map op je PC, bijv. `C:\CurseBot\cursebot`

---

## Stap 1 — Bestanden downloaden

- Ga naar: https://github.com/Die0uwe/cursebot
- Klik groene knop **"Code"** → **"Download ZIP"**
- Pak de ZIP uit naar `C:\CurseBot\`

---

## Stap 2 — .env invullen

- Open de map `C:\CurseBot\cursebot`
- Hernoem `.env.example` naar `.env`
- Open `.env` met Kladblok
- Vul in:

```
DISCORD_TOKEN=jouw_discord_token_hier
RELEASE_CHANNEL_ID=jouw_channel_id_hier
CURSEFORGE_API_KEY=jouw_curseforge_key_hier
CF_AUTHOR_SLUG=dieouwe
CHECK_INTERVAL_MINUTES=10
DATABASE_PATH=cache.db
LOG_LEVEL=INFO
```

- Opslaan

---

## Stap 3 — Eerste keer instellen (eenmalig)

Open een zwart venster (CMD):
- Druk `Windows + R` → typ `cmd` → Enter

Typ deze regels één voor één:

```
cd C:\CurseBot\cursebot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Stap 4 — Bot starten

**Met zichtbaar venster (handig om te testen):**
Dubbelklik op `start_cursebot.bat`

Je ziet dan:
```
[BOT] Online als CurseBot#1234 | Guilds: 1
```

**Op de achtergrond (geen venster):**
Dubbelklik op `start_cursebot_hidden.vbs`

De bot draait nu stil op de achtergrond.
Controleer in Taakbeheer (Ctrl+Shift+Esc) → tabblad Processen → zoek `python`.

---

## Stap 5 — Automatisch opstarten met Windows

Zodat de bot vanzelf start als je PC opstart:

1. Druk `Windows + R` → typ `shell:startup` → Enter
2. Er opent een map
3. Maak daarin een **snelkoppeling** naar `start_cursebot_hidden.vbs`
   - Rechtermuisklik op `start_cursebot_hidden.vbs` → Kopiëren
   - Ga naar de startup map → Rechtermuisklik → Snelkoppeling plakken

Klaar. Volgende keer dat je PC opstart, start de bot automatisch mee.

---

## Bot stoppen

Open Taakbeheer (Ctrl+Shift+Esc) → zoek `python.exe` → Taak beëindigen

---

## Problemen?

- **"python is niet herkend"** → Python opnieuw installeren, vink "Add to PATH" aan
- **"No module named discord"** → Stap 3 opnieuw uitvoeren
- **Bot start maar doet niks** → Controleer je `.env` bestand, alle drie de waarden ingevuld?
