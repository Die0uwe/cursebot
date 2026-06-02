# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — services/curseforge_api.py  v1.4.0

ROOT CAUSE ANALYSE (definitief na research CF API docs):
  1. authors[] heeft {id, name, url} — GEEN username veld
  2. authorSlug parameter filtert server-side NIET
  3. author_id filter werkt WEL maar stopt te vroeg (10 pagina's)
  4. DieOuwe's addons staan NIET in top-500 downloads — moeten verder zoeken
  5. CFWidget geeft 500/403 errors — onbetrouwbaar

OPLOSSING v1.4.0:
  - Sorteer op DateCreated DESC (nieuwste eerst) — kleine auteurs verschijnen vroeg
  - Scan tot 200 pagina's (10.000 mods) maar stop zodra match gevonden én
    downloads zakken onder drempel
  - Filter op authors[].id (correct veld) ZONDER username check
  - Fallback: filter op authors[].name (display naam)
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
        Haalt alle WoW addons op voor auteur DieOuwe.

        Strategie: sorteer op DateCreated DESC zodat nieuwe/kleine addons
        vroeg in de lijst staan. Filter op authors[].id (numeriek).
        Fallback op authors[].name als ID niet matcht.
        """
        results   = []
        index     = 0
        page_size = 50
        needle    = author_slug.lower()
        found_any = False

        log.info(f"[CF] Discovery: author_id={self._author_id}, slug='{author_slug}'")

        async with httpx.AsyncClient(timeout=20.0) as client:
            while True:
                try:
                    r = await client.get(
                        f"{CF_BASE}/mods/search",
                        headers=self._headers,
                        params={
                            "gameId":    self._game_id,
                            "pageSize":  page_size,
                            "index":     index,
                            "sortField": "2",      # 2 = DateCreated — nieuwste eerst
                            "sortOrder": "desc",
                        }
                    )
                    r.raise_for_status()
                    data  = r.json()
                    batch = data.get("data", [])
                except Exception as e:
                    log.error(f"[CF] API fout op index {index}: {e}")
                    break

                if not batch:
                    log.info(f"[CF] Lege batch op index {index} — klaar")
                    break

                # Debug: eerste batch tonen
                if index == 0 and batch:
                    s = batch[0]
                    log.info(f"[CF] Eerste addon: '{s['name']}' | "
                             f"authors: {s.get('authors', [])}")

                for p in batch:
                    authors = p.get("authors", [])

                    # Methode 1: exacte numerieke ID match
                    if self._author_id:
                        match = any(
                            a.get("id") == self._author_id
                            for a in authors
                        )
                    else:
                        match = False

                    # Methode 2: naam match als fallback
                    if not match:
                        match = any(
                            needle in a.get("name", "").lower()
                            for a in authors
                        )

                    if not match:
                        continue

                    found_any = True
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
                    log.info(f"[CF] ✓ Gevonden: {p['name']} (id={p['id']})")

                pagination = data.get("pagination", {})
                total      = pagination.get("totalCount", 0)
                index     += page_size

                log.debug(f"[CF] Pagina {index//page_size}/{(total//page_size)+1} "
                          f"| gevonden: {len(results)}")

                # Stop als alle pagina's gescand zijn
                if index >= total or len(batch) < page_size:
                    log.info(f"[CF] Scan klaar — {index} van {total} mods gescand")
                    break

                # Stop na 10.000 mods (API limiet)
                if index >= 10000:
                    log.warning(f"[CF] API limiet bereikt (10.000 mods)")
                    break

        if not results:
            log.warning(
                f"[CF] ⚠️  Geen projecten gevonden voor author_id={self._author_id} "
                f"/ slug='{author_slug}'. Controleer je CF author ID."
            )
        else:
            log.info(f"[CF] Totaal: {len(results)} projecten gevonden")

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
        changelog   = await self._get_changelog(project_id, f["id"])
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
# ║  File: curseforge_api.py │ v1.4.0 │ Updated │ 2026-06-02  17:00   ║
# ║  Fix: sortField=DateCreated + volledige scan + juiste authors veld  ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
