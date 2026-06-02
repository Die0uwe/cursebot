# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — cogs/curseforge.py  v1.1.0
Monitor cog + stats integratie voor het dashboard.
"""
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
from bot.services.curseforge_api import CurseForgeService
from bot.services.cache import CacheService
from bot.services.claude_api import ClaudeService
from bot.services.stats import STATS
from bot.models.release import AddonProject, AddonRelease
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
        self.monitor_loop.change_interval(minutes=bot.settings.check_interval_minutes)
        self.monitor_loop.start()

    def cog_unload(self):
        self.monitor_loop.cancel()

    @tasks.loop(minutes=10)
    async def monitor_loop(self):
        try:
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            STATS.last_check = now
            STATS.add_log(f"[MONITOR] Check gestart om {now}")
            await self._run_check()
            # Bereken volgende check tijd
            import time
            next_ts = time.time() + (self.bot.settings.check_interval_minutes * 60)
            STATS.next_check = datetime.fromtimestamp(next_ts, tz=timezone.utc).strftime("%H:%M:%S")
        except Exception as exc:
            log.error(f"[MONITOR] Fout: {exc}", exc_info=True)
            STATS.add_log(f"[ERROR] Monitor fout: {exc}")

    @monitor_loop.before_loop
    async def before_monitor(self):
        await self.bot.wait_until_ready()
        log.info("[MONITOR] Bot gereed — start eerste discovery.")
        STATS.add_log("[MONITOR] Eerste project discovery gestart")
        await self._discover_projects(notify=False)

    async def _run_check(self):
        if not self._known_projects:
            await self._discover_projects(notify=True)
            return

        log.debug(f"[MONITOR] Check {len(self._known_projects)} projecten...")
        # Watchlist items ophalen (andere guilds en addons)
        watchlist_items = self.cache.watchlist_all()
        wl_addon_ids    = {item["addon_id"] for item in watchlist_items}
        own_addon_ids   = {p.id for p in self._known_projects}
        extra_ids       = wl_addon_ids - own_addon_ids
        if extra_ids:
            log.debug(f"[MONITOR] {len(extra_ids)} extra watchlist addons controleren")
        channel = self.bot.get_channel(self.bot.settings.release_channel_id)
        if not channel:
            log.error(f"[MONITOR] Channel {self.bot.settings.release_channel_id} niet gevonden.")
            return

        for project in self._known_projects:
            try:
                release = await self.cf.get_latest_file(project.id)
                if not release:
                    continue

                cache_key = f"cf:{project.id}:latest_file"
                cached    = self.cache.get(cache_key)

                if cached and int(cached) == release.file_id:
                    continue
                # Release type filter per guild
                guild_filters = {
                    item["guild_id"]: item.get("release_filter","all")
                    for item in watchlist_items
                    if item["addon_id"] == project.id
                }

                log.info(f"[MONITOR] 🎉 Nieuwe release: {project.name} — {release.display_name}")
                STATS.add_log(f"[RELEASE] {project.name} — {release.display_name}")
                STATS.releases_detected += 1
                self.cache.set(cache_key, str(release.file_id))

                ai_summary = None
                if self.claude and release.changelog:
                    ai_summary = await self.claude.summarize_changelog(project.name, release.changelog)

                embed = build_release_embed(project, release, ai_summary)
                await channel.send(embed=embed)

            except Exception as exc:
                log.error(f"[MONITOR] Fout bij {project.name}: {exc}", exc_info=True)
                STATS.add_log(f"[ERROR] {project.name}: {exc}")

    async def _discover_projects(self, notify: bool = True):
        try:
            projects = await self.cf.get_author_projects(self.bot.settings.cf_author_slug)
            self._known_projects = projects
            STATS.projects_tracked = len(projects)
            STATS.guilds = len(self.bot.guilds)
            log.info(f"[DISCOVER] {len(projects)} projecten geladen voor '{self.bot.settings.cf_author_slug}'")
            STATS.add_log(f"[DISCOVER] {len(projects)} projecten geladen")

            channel = self.bot.get_channel(self.bot.settings.release_channel_id)
            for project in projects:
                release = await self.cf.get_latest_file(project.id)
                if not release:
                    continue
                cache_key = f"cf:{project.id}:latest_file"
                cached    = self.cache.get(cache_key)
                if not notify or cached:
                    self.cache.set(cache_key, str(release.file_id))
                    continue
                if channel:
                    embed = build_release_embed(project, release)
                    await channel.send(embed=embed)
                self.cache.set(cache_key, str(release.file_id))

        except Exception as exc:
            log.error(f"[DISCOVER] Mislukt: {exc}", exc_info=True)
            STATS.add_log(f"[ERROR] Discovery mislukt: {exc}")

    @property
    def known_projects(self) -> list[AddonProject]:
        return self._known_projects


async def setup(bot):
    await bot.add_cog(CurseForgeCog(bot))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: curseforge.py │ Role: Core │ v1.1.0 │ Updated │ 2026-06-02 ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
