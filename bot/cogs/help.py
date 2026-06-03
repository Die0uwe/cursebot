# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — cogs/help.py  v1.0.0

/help slash command met embedded overzicht van alle beschikbare commands.
Publiek zichtbaar (geen admin vereist) — ephemeral zodat het kanaal schoon blijft.
"""
import discord
from discord.ext import commands
from discord import app_commands
from bot.utils.logger import get_logger

log = get_logger(__name__)

SLAYER_GOLD   = 0xF5A623
SLAYER_PURPLE = 0xBF00FF


class HelpCog(commands.Cog, name="Help"):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Toon een overzicht van alle CurseBot slash commands."
    )
    async def help_cmd(self, interaction: discord.Interaction):
        """Publiek /help command — stuurt een ephemeral embed met alle commands."""

        embed = discord.Embed(
            title="⚡ CurseBot — Command Overzicht",
            description=(
                "CurseBot monitort je CurseForge addons en stuurt release-notificaties "
                "naar Discord. Hieronder vind je alle beschikbare slash commands.\n\u200b"
            ),
            color=SLAYER_GOLD,
        )

        # Thumbnail — bot avatar als beschikbaar
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        # ── Setup & Configuratie ───────────────────────────────────────────────
        embed.add_field(
            name="⚙️ Setup & Configuratie",
            value=(
                "`/setup` — Herstart de eerste-keer configuratie\n"
                "`/setchannel` — Koppel een kanaal aan release notificaties\n"
                "`/removechannel` — Verwijder een kanaalconfiguratie\n"
                "`/permissions` — Controleer bot-rechten in een kanaal\n"
                "`/invite` — Genereer een invite link voor andere servers"
            ),
            inline=False,
        )

        # ── Monitoring ─────────────────────────────────────────────────────────
        embed.add_field(
            name="📡 Monitoring",
            value=(
                "`/status` — Toon bot status, getrackte addons en kanaalconfiguratie\n"
                "`/check` — Forceer een directe CurseForge check\n"
                "`/projects` — Toon alle automatisch ontdekte addons\n"
                "`/stats` — Download statistieken per addon\n"
                "`/reset` — Wis de file ID cache (forceert nieuwe notificaties)"
            ),
            inline=False,
        )

        # ── Watchlist ──────────────────────────────────────────────────────────
        embed.add_field(
            name="📋 Watchlist",
            value=(
                "`/watch <query> [filter]` — Voeg een addon toe aan de watchlist\n"
                "  › filter: `all` · `stable` · `stable_beta`\n"
                "`/unwatch <query>` — Verwijder een addon uit de watchlist\n"
                "`/watchlist` — Toon alle getrackte addons voor deze server"
            ),
            inline=False,
        )

        # ── Release Notificaties ───────────────────────────────────────────────
        embed.add_field(
            name="🔔 Release Notificaties",
            value=(
                "CurseBot detecteert automatisch nieuwe releases en stuurt een "
                "embed naar het ingestelde kanaal.\n"
                "Ondersteunt: **Stable** · **Beta** · **Alpha** — per kanaal instelbaar.\n"
                "Bevat: addon logo · file naam · game versions · changelog · download link."
            ),
            inline=False,
        )

        # ── Permissions noot ──────────────────────────────────────────────────
        embed.add_field(
            name="🔒 Rechten",
            value=(
                "Commands met 🔒 vereisen **Administator** rechten.\n"
                "Alle commands zijn alleen zichtbaar voor jezelf (ephemeral)."
            ),
            inline=False,
        )

        embed.set_footer(
            text="CurseBot · Slayer Alliance Edition · dieouwe.nl"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        log.info(f"[HELP] /help gebruikt door {interaction.user} in {interaction.guild}")


async def setup(bot):
    await bot.add_cog(HelpCog(bot))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: help.py │ v1.0.0 │ 2026-06-03                              ║
# ║  Add: /help slash command met volledig command overzicht           ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
