# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — services/curseforge_api.py  v2.0.0

DEFINITIEVE STRATEGIE (na volledige research):
  De CF website gebruikt /mods/search?searchFilter=dieouwe
  Dit is de ENIGE betrouwbare manier om per auteur te zoeken.
  Resultaten worden daarna gefilterd op authors[].id of authors[].name.
  
  authors[] schema: {id: int, name: str, url: str}  (GEEN username!)
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
        self._author_id = author_id
        log.info(f"[CF] Init — author_id={self._author_id}, game_id={self._game_id}")

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_author_projects(self, author_slug: str) -> list[AddonProject]:
        """
        Zoek addons via searchFilter=<naam> — zelfde als CF website.
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
                    r.raise_for_status()
                    data  = r.json()
                    batch = data.get("data", [])
                except Exception as e:
                    log.error(f"[CF] API fout: {e}")
                    break

                if not batch:
                    break

                if index == 0:
                    log.info(f"[CF] Eerste resultaat: '{batch[0]['name']}' | "
                             f"authors: {batch[0].get('authors', [])}")

                for p in batch:
                    authors = p.get("authors", [])
                    # Filter: ID match (best) of naam match (fallback)
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

        log.info(f"[CF] Discovery klaar: {len(results)} projecten")
        return results

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_latest_file(self, project_id: int) -> AddonRelease | None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{CF_BASE}/mods/{project_id}/files",
                headers=self._headers,
                params={"pageSize": 1, "sortOrder": "desc"},
            )
            # 403 = API key probleem of rate limit — log duidelijk en skip
            if r.status_code == 403:
                log.warning(
                    f"[CF] 403 op addon {project_id} — API key ongeldig of rate limit. "
                    f"Controleer CURSEFORGE_API_KEY in .env"
                )
                return None
            r.raise_for_status()
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
# ║  File: curseforge_api.py │ v2.0.0 │ 2026-06-02                    ║
# ║  Fix: searchFilter als primaire methode — zelfde als CF website    ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝

    # ── Zoekfuncties voor watchlist ────────────────────────────────────────────

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def search_addons(
        self, query: str, limit: int = 8
    ) -> list["AddonProject"]:
        """Zoek addons op naam of auteur — voor /watch en /search commands."""
        from bot.models.release import AddonProject
        results = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{CF_BASE}/mods/search",
                headers=self._headers,
                params={
                    "gameId":       self._game_id,
                    "searchFilter": query,
                    "pageSize":     min(limit, 50),
                    "sortField":    "6",   # TotalDownloads
                    "sortOrder":    "desc",
                }
            )
            r.raise_for_status()
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
        from bot.models.release import AddonProject
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    f"{CF_BASE}/mods/{addon_id}",
                    headers=self._headers,
                )
                r.raise_for_status()
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
