# ==============================================================================
# Copyright (C) 2026  DieOuwe (https://www.dieouwe.nl / https://www.slayeralliance.com)
#
# This work is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This work is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# ==============================================================================
import discord
from discord.ext import commands, tasks
from bot.services.curseforge_api import CurseForgeService
from bot.services.cache import CacheService
from bot.services.claude_api import ClaudeService
from bot.models.release import AddonProject, AddonRelease
from bot.utils.embeds import build_release_embed, build_error_embed
from bot.utils.logger import get_logger

log = get_logger(__name__)


class CurseForgeCog(commands.Cog, name="CurseForge Monitor"):
    """Pollt CurseForge en stuurt release-notificaties naar Discord."""

    def __init__(self, bot: commands.Bot):
        self.bot     = bot
        self.cf      = CurseForgeService(
            api_key=bot.settings.curseforge_api_key,
            game_id=bot.settings.cf_game_id,
        )
        self.cache   = CacheService(bot.settings.database_path)
        self.claude  = (
            ClaudeService(bot.settings.anthropic_api_key)
            if bot.settings.summarize_changelogs and bot.settings.anthropic_api_key
            else None
        )
        self._known_projects: list[AddonProject] = []
        # Start loop — interval wordt dynamisch gezet in before_loop
        self.monitor_loop.change_interval(minutes=bot.settings.check_interval_minutes)
        self.monitor_loop.start()

    def cog_unload(self):
        self.monitor_loop.cancel()

    # ─── Monitor loop ──────────────────────────────────────────────────────────

    @tasks.loop(minutes=10)  # Standaard — wordt overschreven door change_interval
    async def monitor_loop(self):
        try:
            await self._run_check()
        except Exception as exc:
            log.error(f"[MONITOR] Onverwachte fout in monitor_loop: {exc}", exc_info=True)

    @monitor_loop.before_loop
    async def before_monitor(self):
        await self.bot.wait_until_ready()
        log.info("[MONITOR] Bot gereed — start eerste project discovery.")
        # Eerste run: laad projecten en sla file IDs op zonder notificaties
        await self._discover_projects(notify=False)

    async def _run_check(self):
        """Controleer alle bekende projecten op nieuwe releases."""
        if not self._known_projects:
            await self._discover_projects(notify=True)
            return

        log.debug(f"[MONITOR] Check {len(self._known_projects)} projecten...")
        channel = self.bot.get_channel(self.bot.settings.release_channel_id)
        if not channel:
            log.error(f"[MONITOR] Release channel {self.bot.settings.release_channel_id} niet gevonden.")
            return

        for project in self._known_projects:
            try:
                release = await self.cf.get_latest_file(project.id)
                if not release:
                    continue

                cache_key = f"cf:{project.id}:latest_file"
                cached = self.cache.get(cache_key)

                if cached and int(cached) == release.file_id:
                    log.debug(f"[MONITOR] {project.name}: geen wijziging (file_id={release.file_id})")
                    continue

                # Nieuwe release gedetecteerd!
                log.info(f"[MONITOR] 🎉 Nieuwe release: {project.name} — {release.display_name}")
                self.cache.set(cache_key, str(release.file_id))

                # Optioneel: AI changelog samenvatting
                ai_summary = None
                if self.claude and release.changelog:
                    ai_summary = await self.claude.summarize_changelog(project.name, release.changelog)

                embed = build_release_embed(project, release, ai_summary)
                await channel.send(embed=embed)

            except Exception as exc:
                log.error(f"[MONITOR] Fout bij check van {project.name}: {exc}", exc_info=True)

    async def _discover_projects(self, notify: bool = True):
        """
        Ontdek alle addons van de auteur.
        Bij notify=False: sla file IDs op maar stuur geen embeds (startup mode).
        """
        try:
            projects = await self.cf.get_author_projects(self.bot.settings.cf_author_slug)
            self._known_projects = projects
            log.info(f"[DISCOVER] {len(projects)} projecten geladen voor '{self.bot.settings.cf_author_slug}'")

            channel = self.bot.get_channel(self.bot.settings.release_channel_id)

            for project in projects:
                release = await self.cf.get_latest_file(project.id)
                if not release:
                    continue

                cache_key = f"cf:{project.id}:latest_file"
                cached = self.cache.get(cache_key)

                if not notify or cached:
                    # Eerste run of al bekend: sla op, geen embed
                    self.cache.set(cache_key, str(release.file_id))
                    continue

                # Nieuwe addon die we nog nooit zagen
                if channel:
                    embed = build_release_embed(project, release)
                    await channel.send(embed=embed)
                self.cache.set(cache_key, str(release.file_id))

        except Exception as exc:
            log.error(f"[DISCOVER] Project discovery mislukt: {exc}", exc_info=True)

    # ─── Properties (voor admin cog) ──────────────────────────────────────────

    @property
    def known_projects(self) -> list[AddonProject]:
        return self._known_projects


async def setup(bot: commands.Bot):
    await bot.add_cog(CurseForgeCog(bot))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : curseforge.py                                       ║
# ║  Role         : Core                                                ║
# ║  Version      : 1.0.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-02  13:45                                     ║
# ║  Status       : Updated                                             ║
# ║  Notes        : CurseForge monitor loop — release detectie          ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
