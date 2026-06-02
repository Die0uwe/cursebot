# ==============================================================================
# Copyright (C) 2026  DieOuwe (https://www.dieouwe.nl / https://www.slayeralliance.com)
#
# This work is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# ==============================================================================
"""
CurseBot — services/curseforge_api.py  v1.0.2-debug
FIX: Debug logging toegevoegd om raw authors[] structuur te inspecteren.
"""
import httpx
import json
from datetime import datetime
from bot.models.release import AddonProject, AddonRelease, ReleaseType
from bot.utils.retry import async_retry
from bot.utils.logger import get_logger

log = get_logger(__name__)

CF_BASE = "https://api.curseforge.com/v1"


class CurseForgeService:
    def __init__(self, api_key: str, game_id: int = 1):
        self._headers = {
            "x-api-key": api_key,
            "Accept": "application/json",
        }
        self._game_id = game_id

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_author_projects(self, author_slug: str) -> list[AddonProject]:
        results: list[AddonProject] = []
        index = 0
        page_size = 50
        author_slug_lower = author_slug.lower()
        first_batch_logged = False

        async with httpx.AsyncClient(timeout=15.0) as client:
            while True:
                r = await client.get(
                    f"{CF_BASE}/mods/search",
                    headers=self._headers,
                    params={
                        "gameId":     self._game_id,
                        "authorSlug": author_slug,
                        "pageSize":   page_size,
                        "index":      index,
                        "sortOrder":  "asc",
                    }
                )
                r.raise_for_status()
                data = r.json()
                batch = data.get("data", [])

                # DEBUG: log de eerste batch raw zodat we de authors structuur zien
                if not first_batch_logged and batch:
                    first_batch_logged = True
                    sample = batch[0]
                    log.warning(
                        f"[CF-DEBUG] Eerste project in batch: '{sample.get('name')}' | "
                        f"authors raw: {json.dumps(sample.get('authors', []))}"
                    )
                elif not first_batch_logged:
                    log.warning(
                        f"[CF-DEBUG] Batch is LEEG voor authorSlug='{author_slug}' "
                        f"— CF geeft niks terug voor deze slug!"
                    )
                    first_batch_logged = True

                for p in batch:
                    # Probeer BEIDE veldnamen: 'username' en 'name' (slug vs display)
                    authors_username = [
                        a.get("username", "").lower()
                        for a in p.get("authors", [])
                    ]
                    authors_name = [
                        a.get("name", "").lower()
                        for a in p.get("authors", [])
                    ]
                    authors_slug = [
                        str(a.get("id", ""))
                        for a in p.get("authors", [])
                    ]

                    match = (
                        author_slug_lower in authors_username or
                        author_slug_lower in authors_name
                    )

                    if not match:
                        continue

                    logo = None
                    if p.get("logo") and p["logo"].get("thumbnailUrl"):
                        logo = p["logo"]["thumbnailUrl"]

                    results.append(AddonProject(
                        id=p["id"],
                        name=p["name"],
                        slug=p["slug"],
                        summary=p.get("summary", ""),
                        url=p.get("links", {}).get(
                            "websiteUrl",
                            f"https://www.curseforge.com/wow/addons/{p['slug']}"
                        ),
                        logo_url=logo,
                        downloads=p.get("downloadCount", 0),
                    ))

                pagination = data.get("pagination", {})
                total = pagination.get("totalCount", 0)
                index += page_size

                if index >= total or len(batch) == 0:
                    break

        log.info(
            f"[CF] {len(results)} projecten gevonden voor auteur '{author_slug}'"
        )
        return results

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_latest_file(self, project_id: int) -> AddonRelease | None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{CF_BASE}/mods/{project_id}/files",
                headers=self._headers,
                params={"pageSize": 1, "sortOrder": "desc"},
            )
            r.raise_for_status()
            files = r.json().get("data", [])

        if not files:
            return None

        f = files[0]
        changelog = await self._get_changelog(project_id, f["id"])

        uploaded_at = None
        try:
            uploaded_at = datetime.fromisoformat(
                f["fileDate"].replace("Z", "+00:00")
            )
        except Exception:
            pass

        return AddonRelease(
            file_id=f["id"],
            file_name=f["fileName"],
            display_name=f.get("displayName") or f["fileName"],
            release_type=ReleaseType(f.get("releaseType", 1)),
            download_url=f.get("downloadUrl"),
            changelog=changelog,
            game_versions=[gv for gv in f.get("gameVersions", [])],
            uploaded_at=uploaded_at,
        )

    @async_retry(retries=2, delay=1.0)
    async def _get_changelog(self, project_id: int, file_id: int) -> str:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{CF_BASE}/mods/{project_id}/files/{file_id}/changelog",
                    headers=self._headers,
                )
                r.raise_for_status()
                raw = r.json().get("data", "")
                return self._strip_html(raw)
        except Exception as exc:
            log.debug(f"[CF] Changelog ophalen mislukt voor {project_id}/{file_id}: {exc}")
            return ""

    @staticmethod
    def _strip_html(html: str) -> str:
        import re
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<li>", "• ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : curseforge_api.py                                    ║
# ║  Role         : Core                                                 ║
# ║  Version      : 1.0.2-debug                                          ║
# ║  Created      : 2026-06-02                                           ║
# ║  Last Updated : 2026-06-02  14:45                                    ║
# ║  Status       : Updated                                              ║
# ║  Notes        : Debug logging om authors[] structuur te inspecteren  ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
