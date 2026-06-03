# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — services/curseforge_api.py  v2.1.1

FIXES v2.1.1:
  - Author ID / Project ID overlap fix: WowTracker gebruikt hetzelfde ID (1417946)
    als de auteur zelf. get_latest_file bypass toegevoegd zodat WowTracker 
    alsnog gecontroleerd kan worden zonder loops/warnings te triggeren.
"""
import asyncio
import httpx
import re
from datetime import datetime
from bot.models.release import AddonProject, AddonRelease, ReleaseType
from bot.utils.retry import async_retry
from bot.utils.logger import get_logger

log = get_logger(__name__)
CF_BASE = "https://api.curseforge.com/v1"

# CF API rate limits: ~300 req/min voor addon keys
# Minimale pauze tussen calls om burst te voorkomen
_REQUEST_DELAY = 0.25  # seconden tussen calls


def _check_response(r: httpx.Response, context: str) -> None:
    """Geef een duidelijke foutmelding op 403/429 voor betere debugging."""
    if r.status_code == 403:
        raise httpx.HTTPStatusError(
            f"[CF] 403 op {context} — API key ongeldig of verlopen. "
            f"Controleer CURSEFORGE_API_KEY in .env",
            request=r.request, response=r
        )
    if r.status_code == 429:
        retry_after = r.headers.get("Retry-After", "60")
        raise httpx.HTTPStatusError(
            f"[CF] 429 Rate limit op {context} — wacht {retry_after}s",
            request=r.request, response=r
        )
    r.raise_for_status()


class CurseForgeService:
    def __init__(self, api_key: str, game_id: int = 1, author_id: int | None = None):
        self._headers   = {"x-api-key": api_key, "Accept": "application/json"}
        self._game_id   = game_id
        self._author_id = author_id
        log.info(f"[CF] Init — author_id={self._author_id}, game_id={self._game_id}")

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_author_projects(self, author_slug: str) -> list[AddonProject]:
        """
        Zoek addons via searchFilter=<naam>.
        Filter resultaten op authors[].id of authors[].name.
        """
        results   = []
        index     = 0
        page_size = 50
        needle    = author_slug.lower()

        log.info(f"[CF] Discovery via searchFilter='{author_slug}' "
                 f"(author_id={self._author_id})")

        async with httpx.AsyncClient(timeout=20.0) as client:
            while True:
                try:
                    r = await client.get(
                        f"{CF_BASE}/mods/search",
                        headers=self._headers,
                        params={
                            "gameId":       self._game_id,
                            "searchFilter": author_slug,
                            "pageSize":     page_size,
                            "index":        index,
                            "sortField":    "2",
                            "sortOrder":    "desc",
                        }
                    )
                    _check_response(r, f"mods/search (index={index})")
                    data  = r.json()
                    batch = data.get("data", [])
                except Exception as e:
                    log.error(f"[CF] API fout: {e}")
                    break

                if not batch:
                    break

                if index == 0 and batch:
                    log.info(f"[CF] Eerste resultaat: '{batch[0]['name']}' | "
                             f"authors: {batch[0].get('authors', [])}")

                for p in batch:
                    authors = p.get("authors", [])
                    match = (
                        (self._author_id and
                         any(a.get("id") == self._author_id for a in authors))
                        or
                        any(needle in a.get("name", "").lower() for a in authors)
                    )
                    if not match:
                        continue

                    logo = (p.get("logo") or {}).get("thumbnailUrl")
                    results.append(AddonProject(
                        id=p["id"],
                        name=p["name"],
                        slug=p["slug"],
                        summary=p.get("summary", ""),
                        url=(p.get("links") or {}).get(
                            "websiteUrl",
                            f"https://www.curseforge.com/wow/addons/{p['slug']}"
                        ),
                        logo_url=logo,
                        downloads=p.get("downloadCount", 0),
                    ))
                    log.info(f"[CF] ✓ {p['name']} (id={p['id']}, "
                             f"dl={p.get('downloadCount',0):,})")

                pagination = data.get("pagination", {})
                total      = pagination.get("totalCount", 0)
                index     += page_size

                if index >= total or len(batch) < page_size or index >= 1000:
                    break

                # Kleine pauze tussen pagina's
                await asyncio.sleep(_REQUEST_DELAY)

        log.info(f"[CF] Discovery klaar: {len(results)} projecten")
        return results

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_latest_file(self, project_id: int) -> AddonRelease | None:
        """
        Haal de meest recente release op voor een addon project.
        """
        # HIER DE FIX: Als het ID 1417946 is (WowTracker), staat de bot het TOE, 
        # omdat we weten dat dit toevallig ook jouw author_id is.
        if self._author_id and project_id == self._author_id and project_id != 1417946:
            log.warning(
                f"[CF] SKIP get_latest_file({project_id}) — "
                f"dit is de CF_AUTHOR_ID, geen project ID! "
                f"Controleer je watchlist/cache op foute entries."
            )
            return None

        await asyncio.sleep(_REQUEST_DELAY)

        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{CF_BASE}/mods/{project_id}/files",
                headers=self._headers,
                params={"pageSize": 1, "sortOrder": "desc"},
            )
            _check_response(r, f"mods/{project_id}/files")
            files = r.json().get("data", [])

        if not files:
            return None

        f = files[0]
        changelog   = await self._get_changelog(project_id, f["id"])
        uploaded_at = None
        try:
            uploaded_at = datetime.fromisoformat(
                f["fileDate"].replace("Z", "+00:00"))
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
            await asyncio.sleep(_REQUEST_DELAY)
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{CF_BASE}/mods/{project_id}/files/{file_id}/changelog",
                    headers=self._headers,
                )
                _check_response(r, f"changelog {project_id}/{file_id}")
                return self._strip_html(r.json().get("data", ""))
        except Exception as exc:
            log.debug(f"[CF] Changelog mislukt {project_id}/{file_id}: {exc}")
            return ""

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def search_addons(self, query: str, limit: int = 8) -> list["AddonProject"]:
        """Zoek addons op naam of auteur — voor /watch en /search commands."""
        results = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{CF_BASE}/mods/search",
                headers=self._headers,
                params={
                    "gameId":       self._game_id,
                    "searchFilter": query,
                    "pageSize":     min(limit, 50),
                    "sortField":    "6",
                    "sortOrder":    "desc",
                }
            )
            _check_response(r, f"mods/search query='{query}'")
            batch = r.json().get("data", [])

        for p in batch[:limit]:
            authors     = p.get("authors", [])
            author_name = authors[0].get("name", "") if authors else ""
            logo        = (p.get("logo") or {}).get("thumbnailUrl")
            results.append(AddonProject(
                id=p["id"],
                name=p["name"],
                slug=p["slug"],
                summary=p.get("summary", ""),
                url=(p.get("links") or {}).get("websiteUrl", ""),
                logo_url=logo,
                downloads=p.get("downloadCount", 0),
                author_name=author_name,
            ))
        log.info(f"[CF] search '{query}': {len(results)} resultaten")
        return results

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_addon_by_id(self, addon_id: int) -> "AddonProject | None":
        """Haal één addon op via numeriek CF project ID."""
        try:
            await asyncio.sleep(_REQUEST_DELAY)
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    f"{CF_BASE}/mods/{addon_id}",
                    headers=self._headers,
                )
                _check_response(r, f"mods/{addon_id}")
                p = r.json().get("data")
            if not p:
                return None
            authors     = p.get("authors", [])
            author_name = authors[0].get("name", "") if authors else ""
            logo        = (p.get("logo") or {}).get("thumbnailUrl")
            return AddonProject(
                id=p["id"],
                name=p["name"],
                slug=p["slug"],
                summary=p.get("summary", ""),
                url=(p.get("links") or {}).get("websiteUrl", ""),
                logo_url=logo,
                downloads=p.get("downloadCount", 0),
                author_name=author_name,
            )
        except Exception as e:
            log.error(f"[CF] get_addon_by_id({addon_id}) mislukt: {e}")
            return None

    @staticmethod
    def _strip_html(html: str) -> str:
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<li>",      "• ", text,  flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>",  "",   text)
        text = re.sub(r"\n{3,}",   "\n\n", text)
        return text.strip()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: curseforge_api.py │ v2.1.1 │ 2026-06-03                    ║
# ║  Fix: Toestaan van ID 1417946 (WowTracker) bypass in check        ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ       ║
# ╚══════════════════════════════════════════════════════════════════════╝