# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — services/curseforge_api.py  v1.2.0
Fix: gebruik CF_AUTHOR_ID (numeriek) als primary filter — veel betrouwbaarder
     dan authorSlug. Fallback naar naam-filter als ID niet geconfigureerd.
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
    def __init__(self, api_key: str, game_id: int = 1, author_id: int | None = None):
        self._headers   = {"x-api-key": api_key, "Accept": "application/json"}
        self._game_id   = game_id
        self._author_id = author_id  # Numerieke CF author ID — meest betrouwbaar

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_author_projects(self, author_slug: str) -> list[AddonProject]:
        """
        Haalt alle addons op voor een auteur.

        Strategie (in volgorde van betrouwbaarheid):
        1. Filter op numerieke author_id via authors[].id  (beste)
        2. Filter op naam/username via authors[].name      (fallback)
        """
        results: list[AddonProject] = []
        index   = 0
        page_size = 50
        needle  = author_slug.lower()

        log.info(f"[CF] Discovery gestart — author_id={self._author_id}, slug='{author_slug}'")

        async with httpx.AsyncClient(timeout=20.0) as client:
            while True:
                params = {
                    "gameId":    self._game_id,
                    "pageSize":  page_size,
                    "index":     index,
                    "sortOrder": "desc",
                    "sortField": "TotalDownloads",
                }
                # Voeg authorSlug toe als hint (helpt soms wel)
                if author_slug:
                    params["authorSlug"] = author_slug

                r = await client.get(
                    f"{CF_BASE}/mods/search",
                    headers=self._headers,
                    params=params,
                )
                r.raise_for_status()
                data  = r.json()
                batch = data.get("data", [])

                # Debug: log eerste batch auteurs
                if index == 0 and batch:
                    sample_authors = batch[0].get("authors", [])
                    log.info(f"[CF-DEBUG] Eerste addon: '{batch[0]['name']}' | "
                             f"authors: {[(a.get('id'), a.get('name'), a.get('username')) for a in sample_authors]}")

                matched_this_page = 0
                for p in batch:
                    authors = p.get("authors", [])

                    if self._author_id:
                        # Methode 1: numerieke ID match — 100% betrouwbaar
                        match = any(a.get("id") == self._author_id for a in authors)
                    else:
                        # Methode 2: naam/username match — case-insensitive
                        match = any(
                            needle in a.get("name", "").lower() or
                            needle in a.get("username", "").lower()
                            for a in authors
                        )

                    if not match:
                        continue

                    matched_this_page += 1
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

                log.debug(f"[CF] Pagina {index//page_size}: {len(batch)} mods, "
                          f"{matched_this_page} gevonden, totaal: {len(results)}")

                # Stop condities
                if len(batch) < page_size or index >= min(total, 10000):
                    break
                # Early exit: als we resultaten hebben en de downloads snel dalen
                if results and index > 500:
                    # Check of laatste addon in batch nog redelijke downloads heeft
                    last_dl = batch[-1].get("downloadCount", 0) if batch else 0
                    if last_dl < 100:
                        log.debug(f"[CF] Early exit op index {index} (downloads < 100)")
                        break

        log.info(f"[CF] {len(results)} projecten gevonden voor '{author_slug}'")
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
# ║  File: curseforge_api.py │ v1.2.0 │ Updated │ 2026-06-02  15:45   ║
# ║  Notes: author_id filter + betere debug logging                     ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
