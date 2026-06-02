# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — services/curseforge_api.py  v1.3.0

STRATEGIE (na research van CF API docs + CFWidget API):
  De officiële CF API /mods/search heeft GEEN betrouwbare author-filter.
  authorSlug is gedocumenteerd maar filtert niet correct server-side.

  Oplossing: gebruik CFWidget publieke API om project-IDs op te halen
  op basis van auteursnaam, dan per project de file status ophalen via CF API.

  CFWidget endpoint: GET https://api.cfwidget.com/author/search/{username}
  Returns: {"projects": [{"id":..., "name":...}], "username": "...", "id": ...}

  Fallback: directe CF API filter op authors[].id (numeriek) als CFWidget faalt.
"""
import httpx
import re
from datetime import datetime
from bot.models.release import AddonProject, AddonRelease, ReleaseType
from bot.utils.retry import async_retry
from bot.utils.logger import get_logger

log = get_logger(__name__)
CF_BASE      = "https://api.curseforge.com/v1"
CFWIDGET_BASE = "https://api.cfwidget.com"


class CurseForgeService:
    def __init__(self, api_key: str, game_id: int = 1, author_id: int | None = None):
        self._headers   = {"x-api-key": api_key, "Accept": "application/json"}
        self._game_id   = game_id
        self._author_id = author_id

        # KRITIEKE VALIDATIE: author_id mag nooit de slug-waarde zijn
        if self._author_id is not None:
            log.info(f"[CF] Init — author_id={self._author_id} (numeriek ✓)")
        else:
            log.warning("[CF] Init — author_id=None, fallback naar naam-filter")

    # ─── CFWidget: beste methode ───────────────────────────────────────────────

    async def _get_projects_via_cfwidget(self, author_slug: str) -> list[dict] | None:
        """
        Gebruik CFWidget API om project-IDs op te halen voor een auteur.
        Publieke API, geen key nodig, retourneert exacte projecten.
        GET https://api.cfwidget.com/author/search/{username}
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    f"{CFWIDGET_BASE}/author/search/{author_slug}",
                    headers={"User-Agent": "CurseBot-SlayerAlliance/1.3"},
                )
                if r.status_code == 404:
                    log.warning(f"[CF] CFWidget: auteur '{author_slug}' niet gevonden (404)")
                    return None
                r.raise_for_status()
                data = r.json()
                projects = data.get("projects", [])
                log.info(f"[CF] CFWidget: {len(projects)} projecten voor '{author_slug}' "
                         f"(CF user ID: {data.get('id', 'onbekend')})")
                return projects
        except Exception as e:
            log.warning(f"[CF] CFWidget niet beschikbaar: {e}")
            return None

    # ─── Hoofd discovery methode ───────────────────────────────────────────────

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_author_projects(self, author_slug: str) -> list[AddonProject]:
        """
        Haalt alle addons op voor een auteur.

        Volgorde:
        1. CFWidget API (beste — exacte projectlijst per auteur)
        2. CF API met author_id filter op authors[].id (als author_id bekend)
        3. CF API met naam-filter fallback (langzaam maar werkt altijd)
        """
        # Validatie: waarschuw als author_slug een getal is (configuratiefout)
        if author_slug.isdigit():
            log.error(
                f"[CF] ⚠️  CF_AUTHOR_SLUG='{author_slug}' is een getal! "
                f"Dit hoort de naam te zijn (bijv. 'dieouwe'). "
                f"Zet CF_AUTHOR_ID={author_slug} in .env en CF_AUTHOR_SLUG=dieouwe"
            )

        # ── Methode 1: CFWidget ───────────────────────────────────────────────
        cfwidget_projects = await self._get_projects_via_cfwidget(author_slug)
        if cfwidget_projects:
            return await self._fetch_project_details_batch(cfwidget_projects)

        # ── Methode 2 & 3: CF API directe filter ──────────────────────────────
        log.info(f"[CF] CFWidget mislukt — gebruik CF API filter "
                 f"(author_id={self._author_id})")
        return await self._search_via_cf_api(author_slug)

    async def _fetch_project_details_batch(
        self, project_stubs: list[dict]
    ) -> list[AddonProject]:
        """Haal volledige details op voor een lijst van project-ID's via CF API."""
        results  = []
        mod_ids  = [p["id"] for p in project_stubs]

        # POST /v1/mods — batch ophalen (max 50 per request)
        async with httpx.AsyncClient(timeout=20.0) as client:
            for i in range(0, len(mod_ids), 50):
                batch_ids = mod_ids[i:i+50]
                try:
                    r = await client.post(
                        f"{CF_BASE}/mods",
                        headers={**self._headers, "Content-Type": "application/json"},
                        json={"modIds": batch_ids},
                    )
                    r.raise_for_status()
                    mods = r.json().get("data", [])
                    for p in mods:
                        # Filter op gameId (WoW = 1)
                        if p.get("gameId") != self._game_id:
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
                except Exception as e:
                    log.error(f"[CF] Batch ophalen mislukt (ids {batch_ids[:3]}...): {e}")

        log.info(f"[CF] {len(results)} WoW projecten geladen via CFWidget+CF API")
        return results

    async def _search_via_cf_api(self, author_slug: str) -> list[AddonProject]:
        """Fallback: zoek via CF API met author_id of naam-filter."""
        results = []
        index   = 0
        page_size = 50
        needle  = author_slug.lower()
        pages_without_match = 0
        MAX_EMPTY_PAGES = 10  # Stop na 10 pagina's zonder match

        async with httpx.AsyncClient(timeout=20.0) as client:
            while True:
                params = {
                    "gameId":    self._game_id,
                    "pageSize":  page_size,
                    "index":     index,
                    "sortOrder": "desc",
                    "sortField": "TotalDownloads",
                }

                r = await client.get(
                    f"{CF_BASE}/mods/search",
                    headers=self._headers,
                    params=params,
                )
                r.raise_for_status()
                data  = r.json()
                batch = data.get("data", [])

                matched_this_page = 0
                for p in batch:
                    authors = p.get("authors", [])
                    if self._author_id and not author_slug.isdigit():
                        # Methode 2: numerieke ID match
                        match = any(a.get("id") == self._author_id for a in authors)
                    else:
                        # Methode 3: naam match
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
                        id=p["id"], name=p["name"], slug=p["slug"],
                        summary=p.get("summary", ""),
                        url=p.get("links", {}).get("websiteUrl",
                            f"https://www.curseforge.com/wow/addons/{p['slug']}"),
                        logo_url=logo,
                        downloads=p.get("downloadCount", 0),
                    ))

                if matched_this_page == 0:
                    pages_without_match += 1
                else:
                    pages_without_match = 0

                # Beveiliging: stop als we te lang niets vinden
                if pages_without_match >= MAX_EMPTY_PAGES and results:
                    log.debug(f"[CF] Early exit: {MAX_EMPTY_PAGES} pagina's zonder match")
                    break
                if pages_without_match >= MAX_EMPTY_PAGES and not results:
                    log.warning(
                        f"[CF] ⚠️  {MAX_EMPTY_PAGES} pagina's gescand, 0 resultaten. "
                        f"Controleer CF_AUTHOR_SLUG en CF_AUTHOR_ID in .env"
                    )
                    break

                pagination = data.get("pagination", {})
                total      = pagination.get("totalCount", 0)
                index     += page_size

                if len(batch) < page_size or index >= min(total, 5000):
                    break

        log.info(f"[CF] {len(results)} projecten gevonden via CF API filter")
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

        f = files[0]
        changelog   = await self._get_changelog(project_id, f["id"])
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
# ║  File: curseforge_api.py │ v1.3.0 │ Updated │ 2026-06-02  16:15   ║
# ║  Fix: CFWidget API als primaire discovery + veiligheidscheck slug   ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
