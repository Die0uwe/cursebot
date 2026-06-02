# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
find_author_id.py — Eenmalig hulpscript
Zoekt de echte CurseForge author ID op voor een gegeven slug.
Run dit EENMALIG: python find_author_id.py
Zet daarna CF_AUTHOR_ID=<gevonden_id> in je .env
"""
import httpx
import asyncio
import os
import sys
from pathlib import Path

# Laad de CF API key uit .env
env = {}
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()

CF_KEY    = env.get("CURSEFORGE_API_KEY", "")
CF_SLUG   = env.get("CF_AUTHOR_SLUG", "dieouwe")
CF_GAMEID = int(env.get("CF_GAME_ID", "1"))

if not CF_KEY:
    print("❌ Geen CURSEFORGE_API_KEY gevonden in .env")
    sys.exit(1)

async def find_author():
    headers = {"x-api-key": CF_KEY, "Accept": "application/json"}

    print(f"\n🔍 Zoeken naar auteur '{CF_SLUG}' op CurseForge...")
    print("─" * 60)

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Methode 1: directe author lookup
        try:
            r = await client.get(
                f"https://api.curseforge.com/v1/mods/search",
                headers=headers,
                params={"gameId": CF_GAMEID, "authorSlug": CF_SLUG, "pageSize": 3}
            )
            data  = r.json()
            batch = data.get("data", [])
            print(f"\n📋 authorSlug param geeft {len(batch)} resultaten:")
            for p in batch[:5]:
                authors = [(a.get("id"), a.get("name"), a.get("username")) for a in p.get("authors", [])]
                print(f"   Addon: {p['name']}")
                print(f"   Authors: {authors}")
        except Exception as e:
            print(f"   Fout: {e}")

        # Methode 2: zoek op naam 'dieouwe' in searchFilter
        try:
            r2 = await client.get(
                f"https://api.curseforge.com/v1/mods/search",
                headers=headers,
                params={"gameId": CF_GAMEID, "searchFilter": CF_SLUG, "pageSize": 5}
            )
            data2  = r2.json()
            batch2 = data2.get("data", [])
            print(f"\n📋 searchFilter='{CF_SLUG}' geeft {len(batch2)} resultaten:")
            for p in batch2[:5]:
                authors = [(a.get("id"), a.get("name"), a.get("username")) for a in p.get("authors", [])]
                print(f"   Addon: {p['name']}")
                print(f"   Authors: {authors}")
        except Exception as e:
            print(f"   Fout: {e}")

        # Methode 3: zoek op bekende addon naam "DelveTracker"
        try:
            r3 = await client.get(
                f"https://api.curseforge.com/v1/mods/search",
                headers=headers,
                params={"gameId": CF_GAMEID, "searchFilter": "DelveTracker", "pageSize": 5}
            )
            data3  = r3.json()
            batch3 = data3.get("data", [])
            print(f"\n📋 searchFilter='DelveTracker' geeft {len(batch3)} resultaten:")
            for p in batch3[:5]:
                authors = [(a.get("id"), a.get("name"), a.get("username")) for a in p.get("authors", [])]
                print(f"   Addon: {p['name']}")
                print(f"   Authors raw: {p.get('authors', [])}")
        except Exception as e:
            print(f"   Fout: {e}")

    print("\n─" * 60)
    print("📌 Kopieer de author 'id' (het getal) en zet in .env:")
    print("   CF_AUTHOR_ID=<het_getal>")

asyncio.run(find_author())
