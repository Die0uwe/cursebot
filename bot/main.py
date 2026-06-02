# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — main.py  v1.1.0
Entry point. Start de bot + het web dashboard op poort 5000.
"""
import asyncio
import discord
from discord.ext import commands
from bot.config import Settings
from bot.utils.logger import configure_root_logger, get_logger
from bot.services.stats import STATS

log = get_logger(__name__)

COGS = ["bot.cogs.curseforge", "bot.cogs.admin", "bot.cogs.watchlist"]


class CurseBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!cb.", intents=intents, help_command=None)
        self.settings = settings

    async def setup_hook(self):
        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info(f"[BOT] Cog geladen: {cog}")
                STATS.add_log(f"Cog geladen: {cog}")
            except Exception as exc:
                log.error(f"[BOT] Cog laden mislukt ({cog}): {exc}", exc_info=True)
                STATS.add_log(f"[ERROR] Cog mislukt: {cog}: {exc}")

        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"[BOT] Slash commands gesync naar guild {self.settings.guild_id}")
        else:
            await self.tree.sync()
            log.info("[BOT] Slash commands globaal gesync")

    async def on_ready(self):
        STATS.guilds    = len(self.guilds)
        STATS.cf_author = self.settings.cf_author_slug
        STATS.check_interval_min = self.settings.check_interval_minutes
        STATS.add_log(f"[BOT] Online als {self.user} | Guilds: {len(self.guilds)}")
        log.info(f"[BOT] Online als {self.user} | Guilds: {len(self.guilds)}")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="CurseForge · Slayer Alliance"
        ))

    async def on_application_command_error(self, interaction, error):
        log.error(f"[BOT] Slash fout: {error}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Fout: `{error}`", ephemeral=True)


async def main():
    settings = Settings()
    configure_root_logger(settings.log_level)
    log.info("[BOT] CurseBot start — Slayer Alliance Edition")
    log.info(f"[BOT] Author: {settings.cf_author_slug} | Interval: {settings.check_interval_minutes}m")
    STATS.add_log("[BOT] CurseBot gestart")
    STATS.cf_author = settings.cf_author_slug

    # Start het web dashboard in een achtergrond thread
    try:
        from dashboard import start_dashboard_thread
        start_dashboard_thread(port=5000)
        log.info("[BOT] Dashboard gestart op http://localhost:5000")
        STATS.add_log("[BOT] Dashboard actief op poort 5000")
    except Exception as e:
        log.warning(f"[BOT] Dashboard kon niet starten: {e}")

    bot = CurseBot(settings)
    async with bot:
        await bot.start(settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: main.py │ Role: Core │ v1.1.0 │ Updated │ 2026-06-02 15:30 ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
