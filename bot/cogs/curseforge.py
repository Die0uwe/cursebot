# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — cogs/curseforge.py  v2.0.0
Monitor cog met multi-channel support, download stats, watchlist tracking.
"""
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
import time

from bot.services.curseforge_api import CurseForgeService
from bot.services.cache import CacheService
from bot.services.claude_api import ClaudeService
from bot.services.stats import STATS
from bot.models.release import AddonProject, AddonRelease, ReleaseType
from bot.utils.embeds import build_release_embed
from bot.utils.logger import get_logger

log = get_logger(__name__)


class CurseForgeCog(commands.Cog, name="CurseForge Monitor"):
    def __init__(self, bot):
        self.bot    = bot
        self.cf     = CurseForgeService(
            api_key=bot.settings.curseforge_api_key,
            game_id=bot.settings.cf_game_id,
            author_id=bot.settings.cf_author_id,
        )
        self.cache  = CacheService(bot.settings.database_path)
        self.claude = (
            ClaudeService(bot.settings.anthropic_api_key)
            if bot.settings.summarize_changelogs and bot.settings.anthropic_api_key
            else None
        )
        self._known_projects: list[AddonProject] = []
        self.monitor_loop.change_interval(
            minutes=bot.settings.check_interval_minutes
        )
        self.monitor_loop.start()

    def cog_unload(self):
        self.monitor_loop.cancel()

    # ── Monitor loop ───────────────────────────────────────────────────────────
    @tasks.loop(minutes=10)
    async def monitor_loop(self):
        # Check force_check flag vanuit dashboard/UI
        if STATS.force_check:
            STATS.force_check = False
            log.info("[MONITOR] Handmatige check getriggerd")

        try:
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            STATS.last_check = now
            STATS.add_log(f"[MONITOR] Check gestart om {now}")
            await self._run_check()
            next_ts = time.time() + (self.bot.settings.check_interval_minutes * 60)
            STATS.next_check = datetime.fromtimestamp(
                next_ts, tz=timezone.utc
            ).strftime("%H:%M:%S")
        except Exception as exc:
            log.error(f"[MONITOR] Fout: {exc}", exc_info=True)
            STATS.add_log(f"[ERROR] Monitor: {exc}")

    @monitor_loop.before_loop
    async def before_monitor(self):
        await self.bot.wait_until_ready()
        log.info("[MONITOR] Bot gereed — start eerste discovery.")
        STATS.add_log("[MONITOR] Eerste discovery gestart")
        await self._discover_projects(notify=False)

    # ── Check logica ───────────────────────────────────────────────────────────
    async def _run_check(self):
        # Combineer eigen projecten + watchlist items
        all_addon_ids = set(p.id for p in self._known_projects)

        # Watchlist items ophalen
        wl_items    = self.cache.watchlist_all()
        wl_by_addon = {}  # addon_id -> list[dict]
        for item in wl_items:
            aid = item["addon_id"]
            wl_by_addon.setdefault(aid, []).append(item)
            all_addon_ids.add(aid)

        # Wijs guilds toe aan eigen projecten
        for p in self._known_projects:
            if p.id not in wl_by_addon:
                # Voeg toe als default guild
                wl_by_addon[p.id] = [{
                    "guild_id":       str(self.bot.settings.release_channel_id),
                    "addon_id":       p.id,
                    "addon_name":     p.name,
                    "release_filter": "all",
                }]

        log.debug(f"[MONITOR] {len(all_addon_ids)} unieke addons controleren")

        for addon_id in all_addon_ids:
            try:
                release = await self.cf.get_latest_file(addon_id)
                if not release:
                    continue

                # Download stats opslaan
                self.cache.stats_record(addon_id, 0)  # placeholder
                meta = self.cache.addon_meta_get(addon_id)

                cache_key = f"cf:{addon_id}:latest_file"
                cached    = self.cache.get(cache_key)

                if cached and int(cached) == release.file_id:
                    continue

                # Nieuwe release gevonden
                addon_name = meta["name"] if meta else f"Addon #{addon_id}"
                log.info(f"[MONITOR] 🎉 {addon_name} — {release.display_name}")
                STATS.add_log(f"[RELEASE] {addon_name} — {release.display_name}")
                STATS.releases_detected += 1
                self.cache.set(cache_key, str(release.file_id))

                # AI samenvatting
                ai_summary = None
                if self.claude and release.changelog:
                    ai_summary = await self.claude.summarize_changelog(
                        addon_name, release.changelog
                    )

                # Stuur naar de juiste kanalen per guild
                await self._notify_guilds(
                    addon_id=addon_id,
                    addon_name=addon_name,
                    release=release,
                    wl_entries=wl_by_addon.get(addon_id, []),
                    ai_summary=ai_summary,
                )

            except Exception as exc:
                log.error(f"[MONITOR] Fout bij addon {addon_id}: {exc}", exc_info=True)
                STATS.add_log(f"[ERROR] Addon {addon_id}: {exc}")

    async def _notify_guilds(
        self,
        addon_id: int,
        addon_name: str,
        release: AddonRelease,
        wl_entries: list[dict],
        ai_summary: str | None,
    ):
        """
        Stuur release embed naar de juiste kanalen.
        Multi-channel: per guild kijken welk kanaal het juiste release type ontvangt.
        """
        notified_channels = set()

        # Haal addon info op voor embed
        meta = self.cache.addon_meta_get(addon_id)
        own_project = next(
            (p for p in self._known_projects if p.id == addon_id), None
        )

        for entry in wl_entries:
            guild_id        = entry.get("guild_id", "0")
            release_filter  = entry.get("release_filter", "all")

            # Controleer release filter
            if not release.matches_filter(release_filter):
                continue

            # Bepaal doelkanaal via channel_config
            # Probeer specifiek type → fallback naar 'all' → fallback naar settings
            target_ch_id = (
                self.cache.channel_get(guild_id, release.release_type.name.lower())
                or self.cache.channel_get(guild_id, "all")
                or self.bot.settings.release_channel_id
            )

            if target_ch_id in notified_channels:
                continue  # Zelfde kanaal niet twee keer

            channel = self.bot.get_channel(int(target_ch_id))
            if not channel:
                continue

            # Bouw embed
            if own_project:
                embed = build_release_embed(own_project, release, ai_summary)
            else:
                # Watchlist addon — maak een AddonProject stub
                from bot.models.release import AddonProject as AP
                stub = AP(
                    id=addon_id,
                    name=meta["name"] if meta else addon_name,
                    slug=meta.get("slug","") if meta else "",
                    summary=meta.get("summary","") if meta else "",
                    url=meta.get("url","") if meta else "",
                    logo_url=meta.get("logo_url") if meta else None,
                    downloads=meta.get("downloads",0) if meta else 0,
                    author_name=meta.get("author_name","") if meta else "",
                )
                embed = build_release_embed(stub, release, ai_summary)

            await channel.send(embed=embed)
            notified_channels.add(target_ch_id)
            log.info(f"[NOTIFY] {addon_name} → #{channel.name} (guild {guild_id})")

    # ── Discovery ──────────────────────────────────────────────────────────────
    async def _discover_projects(self, notify: bool = True):
        try:
            projects = await self.cf.get_author_projects(
                self.bot.settings.cf_author_slug
            )
            self._known_projects = projects
            STATS.projects_tracked = len(projects)
            STATS.guilds           = len(self.bot.guilds)
            STATS.project_list     = [
                {
                    "id": p.id, "name": p.name, "slug": p.slug,
                    "url": p.url, "downloads": p.downloads,
                    "logo_url": p.logo_url, "summary": p.summary,
                    "author_name": p.author_name,
                }
                for p in projects
            ]

            log.info(
                f"[DISCOVER] {len(projects)} projecten voor "
                f"'{self.bot.settings.cf_author_slug}'"
            )
            STATS.add_log(f"[DISCOVER] {len(projects)} projecten geladen")

            # Cache metadata + initialiseer file tracking
            for p in projects:
                self.cache.addon_meta_set(p.id, {
                    "name": p.name, "slug": p.slug,
                    "author_name": p.author_name, "summary": p.summary,
                    "url": p.url, "logo_url": p.logo_url,
                    "downloads": p.downloads,
                })
                # Download stats bijhouden
                self.cache.stats_record(p.id, p.downloads)

                release   = await self.cf.get_latest_file(p.id)
                if not release:
                    continue
                cache_key = f"cf:{p.id}:latest_file"
                cached    = self.cache.get(cache_key)

                if not notify or cached:
                    self.cache.set(cache_key, str(release.file_id))
                    continue

                channel = self.bot.get_channel(self.bot.settings.release_channel_id)
                if channel:
                    embed = build_release_embed(p, release)
                    await channel.send(embed=embed)
                self.cache.set(cache_key, str(release.file_id))

        except Exception as exc:
            log.error(f"[DISCOVER] Mislukt: {exc}", exc_info=True)
            STATS.add_log(f"[ERROR] Discovery: {exc}")

    @property
    def known_projects(self) -> list[AddonProject]:
        return self._known_projects


async def setup(bot):
    await bot.add_cog(CurseForgeCog(bot))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: curseforge.py │ v2.0.0 │ 2026-06-02                        ║
# ║  Multi-channel · download stats · watchlist tracking               ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
