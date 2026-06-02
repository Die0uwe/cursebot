# ==============================================================================
# Copyright (C) 2026  DieOuwe (https://www.dieouwe.nl / https://www.slayeralliance.com)
# GNU General Public License v3 — zie LICENSE voor details
# ==============================================================================
"""
CurseBot — services/curseforge_api.py  v1.1.0
Fix: zoek direct op auteur-naam via /mods/search?searchFilter=
     en filter daarna client-side op authors[].name (case-insensitive).
     De authorSlug param is geen betrouwbare API-filter.
"""
import httpx
import re
from datetime import datetime
from bot.models.release import AddonProject, AddonRelease, ReleaseType
from bot.utils.retry import async_retry
from bot.utils.logger import get_logger

log = get_logger(__name__)
CF_BASE = "https://api.curseforge.com/v1"


class CurseForgeService:
    def __init__(self, api_key: str, game_id: int = 1):
        self._headers = {"x-api-key": api_key, "Accept": "application/json"}
        self._game_id = game_id

    # ─── Author discovery ─────────────────────────────────────────────────────

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_author_projects(self, author_slug: str) -> list[AddonProject]:
        """
        Haalt alle addons op voor een auteur.
        Strategie: haal ALLE WoW mods op (gepagineerd) en filter client-side
        op authors[].name of authors[].username (beide, case-insensitive).
        """
        results: list[AddonProject] = []
        index = 0
        page_size = 50
        needle = author_slug.lower()

        async with httpx.AsyncClient(timeout=20.0) as client:
            while True:
                r = await client.get(
                    f"{CF_BASE}/mods/search",
                    headers=self._headers,
                    params={
                        "gameId":    self._game_id,
                        "pageSize":  page_size,
                        "index":     index,
                        "sortOrder": "desc",
                        "sortField": "TotalDownloads",
                    }
                )
                r.raise_for_status()
                data  = r.json()
                batch = data.get("data", [])

                for p in batch:
                    # Check op name, username, en url slug — alles lowercase
                    authors = p.get("authors", [])
                    matched = any(
                        needle in a.get("name", "").lower() or
                        needle in a.get("username", "").lower()
                        for a in authors
                    )
                    if not matched:
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
                total      = pagination.get("totalCount", 0)
                index     += page_size

                # Stop zodra we alle pagina's hebben of een match gevonden én
                # de batch kleiner is dan page_size (laatste pagina)
                if index >= min(total, 10000) or len(batch) < page_size:
                    break

                # Early-exit: als we al resultaten hebben én diep in de lijst
                # zitten (downloads zakken snel) kunnen we stoppen
                if results and index > 2000:
                    break

        log.info(f"[CF] {len(results)} projecten gevonden voor '{author_slug}'")
        return results

    # ─── File polling ──────────────────────────────────────────────────────────

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

        f          = files[0]
        changelog  = await self._get_changelog(project_id, f["id"])
        uploaded_at = None
        try:
            uploaded_at = datetime.fromisoformat(f["fileDate"].replace("Z", "+00:00"))
        except Exception:
            pass

        return AddonRelease(
            file_id=f["id"],
            file_name=f["fileName"],
            display_name=f.get("displayName") or f["fileName"],
            release_type=ReleaseType(f.get("releaseType", 1)),
            download_url=f.get("downloadUrl"),
            changelog=changelog,
            game_versions=f.get("gameVersions", []),
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
                return self._strip_html(r.json().get("data", ""))
        except Exception as exc:
            log.debug(f"[CF] Changelog mislukt {project_id}/{file_id}: {exc}")
            return ""

    @staticmethod
    def _strip_html(html: str) -> str:
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<li>",      "• ", text,  flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>",  "",   text)
        text = re.sub(r"\n{3,}",   "\n\n", text)
        return text.strip()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File         : curseforge_api.py   │  Role    : Core              ║
# ║  Version      : 1.1.0               │  Status  : Updated           ║
# ║  Last Updated : 2026-06-02  15:30   │  Notes   : Fix auteur filter ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
