# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""CurseBot — main.py  v2.0.0"""
import asyncio
import discord
from discord.ext import commands
from bot.config import Settings
from bot.utils.logger import configure_root_logger, get_logger
from bot.services.stats import STATS

log = get_logger(__name__)

COGS = [
    "bot.cogs.onboarding",   # Eerst laden — guild join events
    "bot.cogs.curseforge",
    "bot.cogs.admin",
    "bot.cogs.watchlist",
]


class CurseBot(commands.Bot):
    def __init__(self, settings: Settings):
        # Intents: guild events voor on_guild_join
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(
            command_prefix="!cb.",
            intents=intents,
            help_command=None
        )
        self.settings = settings

    async def setup_hook(self):
        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info(f"[BOT] Cog geladen: {cog}")
                STATS.add_log(f"Cog geladen: {cog.split('.')[-1]}")
            except Exception as exc:
                log.error(f"[BOT] Cog mislukt ({cog}): {exc}", exc_info=True)
                STATS.add_log(f"[ERROR] Cog mislukt: {cog}: {exc}")

        # Slash commands syncen
        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"[BOT] Slash commands gesync naar guild {self.settings.guild_id}")
        else:
            await self.tree.sync()
            log.info("[BOT] Slash commands globaal gesync")

    async def on_ready(self):
        STATS.guilds             = len(self.guilds)
        STATS.cf_author          = self.settings.cf_author_slug
        STATS.cf_author_id       = self.settings.cf_author_id
        STATS.check_interval_min = self.settings.check_interval_minutes
        STATS.bot_online         = True
        STATS.add_log(f"[BOT] Online als {self.user} | Guilds: {len(self.guilds)}")
        log.info(f"[BOT] Online als {self.user} | Guilds: {len(self.guilds)}")

        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="CurseForge · Slayer Alliance"
        ))

    async def on_application_command_error(self, interaction, error):
        log.error(f"[BOT] Slash fout: {error}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ Fout: `{error}`", ephemeral=True
            )

    async def close(self):
        STATS.bot_online = False
        await super().close()


async def main():
    settings = Settings()
    configure_root_logger(settings.log_level)
    log.info("[BOT] CurseBot start — Slayer Alliance Edition")
    log.info(f"[BOT] Author: {settings.cf_author_slug} | Interval: {settings.check_interval_minutes}m")
    STATS.add_log("[BOT] Gestart")
    STATS.cf_author    = settings.cf_author_slug
    STATS.cf_author_id = settings.cf_author_id

    # Dashboard starten
    try:
        from dashboard import start_dashboard_thread
        start_dashboard_thread(port=settings.dashboard_port)
        log.info(f"[BOT] Dashboard actief op http://localhost:{settings.dashboard_port}")
    except Exception as e:
        log.warning(f"[BOT] Dashboard niet gestart: {e}")

    bot = CurseBot(settings)
    async with bot:
        await bot.start(settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: main.py │ v2.0.0 │ 2026-06-02                              ║
# ║  Onboarding cog eerst · guild intents · bot_online flag            ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
