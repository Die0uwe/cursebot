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
from discord import app_commands
from discord.ext import commands
from bot.utils.embeds import build_status_embed, build_error_embed
from bot.utils.logger import get_logger

log = get_logger(__name__)


def is_admin():
    """Check: enkel guild admins mogen admin-commando's gebruiken."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(
            "❌ Je hebt geen administrator-rechten voor dit commando.",
            ephemeral=True,
        )
        return False
    return app_commands.check(predicate)


class AdminCog(commands.Cog, name="Admin"):
    """Beheer-commando's voor CurseBot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_cf_cog(self):
        return self.bot.cogs.get("CurseForge Monitor")

    # /status
    @app_commands.command(name="status", description="Toon CurseBot monitor status.")
    @is_admin()
    async def status(self, interaction: discord.Interaction):
        cf = self._get_cf_cog()
        projects = cf.known_projects if cf else []
        embed = build_status_embed(projects, self.bot.settings.check_interval_minutes)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /check — forceer onmiddellijke check
    @app_commands.command(name="check", description="Forceer onmiddellijke CurseForge check.")
    @is_admin()
    async def force_check(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cf = self._get_cf_cog()
        if not cf:
            await interaction.followup.send("❌ CurseForge cog niet geladen.", ephemeral=True)
            return
        try:
            await cf._run_check()
            await interaction.followup.send("✅ Check uitgevoerd.", ephemeral=True)
        except Exception as exc:
            log.error(f"[ADMIN] Force check mislukt: {exc}", exc_info=True)
            await interaction.followup.send(f"❌ Fout: `{exc}`", ephemeral=True)

    # /projects — lijst van getrackte addons
    @app_commands.command(name="projects", description="Toon alle getrackte CurseForge projecten.")
    @is_admin()
    async def projects(self, interaction: discord.Interaction):
        cf = self._get_cf_cog()
        if not cf or not cf.known_projects:
            await interaction.response.send_message("⚠️ Geen projecten geladen.", ephemeral=True)
            return

        lines = [
            f"`{i+1}.` [{p.name}]({p.url}) — ID: `{p.id}` — {p.downloads:,} downloads"
            for i, p in enumerate(cf.known_projects)
        ]
        embed = discord.Embed(
            title=f"📦 Tracked Projects ({len(cf.known_projects)})",
            description="\n".join(lines[:20]),
            color=0xBF00FF,  # Slayer purple
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /reset — verwijder alle cache
    @app_commands.command(name="reset", description="Reset de file ID cache (veroorzaakt herdetectie van alle releases).")
    @is_admin()
    async def reset_cache(self, interaction: discord.Interaction):
        from bot.services.cache import CacheService
        cache = CacheService(self.bot.settings.database_path)
        cache.wipe()
        log.warning(f"[ADMIN] Cache gereset door {interaction.user}")
        await interaction.response.send_message(
            "⚠️ Cache gewist. Volgende check zal alle huidige releases opnieuw detecteren.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : admin.py                                            ║
# ║  Role         : Core                                                ║
# ║  Version      : 1.0.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-02  13:45                                     ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Admin slash commands: /status /check /reset         ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
