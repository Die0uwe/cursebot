"""
CurseBot — services/curseforge_api.py
Alle CurseForge API-aanroepen voor author project discovery en file polling.

Rate limits CurseForge API (v1):
  - 300 req/min per key (burst)
  - 10.000 req/dag
  Met 10-minuten interval + ~20 projecten = ~144 req/dag — ruim binnen limiet.
"""
import httpx
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
        self._game_id = game_id  # 1 = WoW

    # ─── Author discovery ─────────────────────────────────────────────────────

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_author_projects(self, author_slug: str) -> list[AddonProject]:
        """
        Haalt alle addons op voor een auteur via search-endpoint.
        Pagineert automatisch als er meer dan 50 projecten zijn.
        """
        results: list[AddonProject] = []
        index = 0
        page_size = 50

        async with httpx.AsyncClient(timeout=15.0) as client:
            while True:
                r = await client.get(
                    f"{CF_BASE}/mods/search",
                    headers=self._headers,
                    params={
                        "gameId":   self._game_id,
                        "authorSlug": author_slug,
                        "pageSize": page_size,
                        "index":    index,
                        "sortOrder": "asc",
                    }
                )
                r.raise_for_status()
                data = r.json()
                batch = data.get("data", [])

                for p in batch:
                    logo = None
                    if p.get("logo") and p["logo"].get("thumbnailUrl"):
                        logo = p["logo"]["thumbnailUrl"]
                    results.append(AddonProject(
                        id=p["id"],
                        name=p["name"],
                        slug=p["slug"],
                        summary=p.get("summary", ""),
                        url=p.get("links", {}).get("websiteUrl", f"https://www.curseforge.com/wow/addons/{p['slug']}"),
                        logo_url=logo,
                        downloads=p.get("downloadCount", 0),
                    ))

                pagination = data.get("pagination", {})
                total = pagination.get("totalCount", 0)
                index += page_size

                if index >= total or len(batch) == 0:
                    break

        log.info(f"[CF] {len(results)} projecten gevonden voor auteur '{author_slug}'")
        return results

    # ─── File polling ──────────────────────────────────────────────────────────

    @async_retry(retries=3, delay=2.0, backoff=2.0)
    async def get_latest_file(self, project_id: int) -> AddonRelease | None:
        """
        Haalt de meest recente file op voor een project.
        Sorteert op fileDate descending — geeft altijd de nieuwste terug.
        """
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
            game_versions=[gv for gv in f.get("gameVersions", [])],
            uploaded_at=uploaded_at,
        )

    @async_retry(retries=2, delay=1.0)
    async def _get_changelog(self, project_id: int, file_id: int) -> str:
        """Haalt de changelog op voor een specifieke file."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{CF_BASE}/mods/{project_id}/files/{file_id}/changelog",
                    headers=self._headers,
                )
                r.raise_for_status()
                # CurseForge geeft HTML terug — strip simpele tags
                raw = r.json().get("data", "")
                return self._strip_html(raw)
        except Exception as exc:
            log.debug(f"[CF] Changelog ophalen mislukt voor {project_id}/{file_id}: {exc}")
            return ""

    @staticmethod
    def _strip_html(html: str) -> str:
        """Verwijder HTML-tags voor leesbare Discord-tekst."""
        import re
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<li>", "• ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
