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
import asyncio
import discord
from discord.ext import commands
from bot.config import Settings
from bot.utils.logger import configure_root_logger, get_logger

log = get_logger(__name__)

COGS = [
    "bot.cogs.curseforge",
    "bot.cogs.admin",
]


class CurseBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        # message_content niet nodig — we gebruiken alleen slash commands
        super().__init__(
            command_prefix="!cb.",        # Prefix commando's uitgeschakeld in de praktijk
            intents=intents,
            help_command=None,
        )
        self.settings = settings

    async def setup_hook(self):
        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info(f"[BOT] Cog geladen: {cog}")
            except Exception as exc:
                log.error(f"[BOT] Cog laden mislukt ({cog}): {exc}", exc_info=True)

        # Slash commands syncronen
        if self.settings.guild_id:
            # Dev mode: sync naar specifieke guild (onmiddellijk)
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"[BOT] Slash commands gesynchroon naar guild {self.settings.guild_id} (dev mode)")
        else:
            # Prod: globale sync (kan tot 1 uur duren)
            await self.tree.sync()
            log.info("[BOT] Slash commands globaal gesynchroon (kan tot 1 uur duren)")

    async def on_ready(self):
        log.info(f"[BOT] Online als {self.user} | Guilds: {len(self.guilds)}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="CurseForge · Slayer Alliance"
            )
        )

    async def on_application_command_error(self, interaction: discord.Interaction, error: Exception):
        log.error(f"[BOT] Slash command fout: {error}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ Onverwachte fout: `{error}`", ephemeral=True
            )


async def main():
    settings = Settings()
    configure_root_logger(settings.log_level)
    log.info("[BOT] CurseBot start — Slayer Alliance Edition")
    log.info(f"[BOT] Author: {settings.cf_author_slug} | Interval: {settings.check_interval_minutes}m")

    bot = CurseBot(settings)
    async with bot:
        await bot.start(settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : main.py                                             ║
# ║  Role         : Core                                                ║
# ║  Version      : 1.0.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-02  13:45                                     ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Entry point — CurseBot startup & cog loader         ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
