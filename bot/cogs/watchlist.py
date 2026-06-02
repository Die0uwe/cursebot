# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — cogs/watchlist.py  v1.0.0

Slash commands voor addon watchlist beheer:
  /watch   [naam|id|auteur] — voeg addon(s) toe aan watchlist
  /unwatch [naam|id]        — verwijder addon uit watchlist
  /watchlist                — toon alle getrackte addons
  /search  [query]          — zoek addons op CurseForge
"""
import discord
from discord.ext import commands
from discord import app_commands
from bot.services.curseforge_api import CurseForgeService
from bot.services.cache import CacheService
from bot.utils.logger import get_logger

log = get_logger(__name__)

MAX_WATCHLIST = 50  # Max addons per guild


class WatchlistCog(commands.Cog, name="Watchlist"):
    def __init__(self, bot):
        self.bot   = bot
        self.cf    = CurseForgeService(
            api_key=bot.settings.curseforge_api_key,
            game_id=bot.settings.cf_game_id,
            author_id=bot.settings.cf_author_id,
        )
        self.cache = CacheService(bot.settings.database_path)

    # ── /watch ─────────────────────────────────────────────────────────────────

    @app_commands.command(
        name="watch",
        description="Voeg een WoW addon toe aan de release watchlist."
    )
    @app_commands.describe(
        query="Addon naam, CurseForge project ID, of auteursnaam",
        filter="Welke release types tracken?"
    )
    @app_commands.choices(filter=[
        app_commands.Choice(name="Alles (stable + beta + alpha)", value="all"),
        app_commands.Choice(name="Alleen Stable",                  value="stable"),
        app_commands.Choice(name="Stable + Beta",                  value="stable_beta"),
    ])
    async def watch(
        self,
        interaction: discord.Interaction,
        query: str,
        filter: app_commands.Choice[str] | None = None,
    ):
        await interaction.response.defer(ephemeral=True)
        guild_id     = str(interaction.guild_id)
        release_filter = filter.value if filter else "all"

        # Check watchlist limiet
        count = self.cache.watchlist_count(guild_id)
        if count >= MAX_WATCHLIST:
            await interaction.followup.send(
                f"❌ Watchlist vol ({MAX_WATCHLIST} addons max). "
                f"Gebruik `/unwatch` om er een te verwijderen.",
                ephemeral=True
            )
            return

        # Probeer als numeriek ID
        if query.strip().isdigit():
            addon_id = int(query.strip())
            addon    = await self.cf.get_addon_by_id(addon_id)
            if not addon:
                await interaction.followup.send(
                    f"❌ Geen addon gevonden met ID `{addon_id}`.",
                    ephemeral=True
                )
                return
            added = self.cache.watchlist_add(
                guild_id=guild_id, addon_id=addon.id,
                addon_name=addon.name, addon_slug=addon.slug,
                addon_url=addon.url, author_name=addon.author_name,
                downloads=addon.downloads, logo_url=addon.logo_url,
                release_filter=release_filter,
                added_by=str(interaction.user)
            )
            if added:
                embed = self._watch_embed(addon, release_filter, "toegevoegd")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(
                    f"ℹ️ **{addon.name}** staat al in de watchlist.",
                    ephemeral=True
                )
            return

        # Zoek op naam of auteur
        results = await self.cf.search_addons(query, limit=5)
        if not results:
            await interaction.followup.send(
                f"❌ Geen addons gevonden voor `{query}`.",
                ephemeral=True
            )
            return

        if len(results) == 1:
            addon = results[0]
            added = self.cache.watchlist_add(
                guild_id=guild_id, addon_id=addon.id,
                addon_name=addon.name, addon_slug=addon.slug,
                addon_url=addon.url, author_name=addon.author_name,
                downloads=addon.downloads, logo_url=addon.logo_url,
                release_filter=release_filter,
                added_by=str(interaction.user)
            )
            if added:
                embed = self._watch_embed(addon, release_filter, "toegevoegd")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(
                    f"ℹ️ **{addon.name}** staat al in de watchlist.",
                    ephemeral=True
                )
        else:
            # Meerdere resultaten — toon keuzelijst
            embed = discord.Embed(
                title="🔍 Meerdere resultaten gevonden",
                description="Gebruik het ID om de juiste addon toe te voegen:",
                color=0xf5a623
            )
            for i, a in enumerate(results, 1):
                embed.add_field(
                    name=f"{i}. {a.name}",
                    value=(
                        f"**Auteur:** {a.author_name}\n"
                        f"**ID:** `{a.id}`\n"
                        f"**Downloads:** {a.downloads:,}\n"
                        f"[CurseForge]({a.url})"
                    ),
                    inline=True
                )
            embed.set_footer(text=f"Gebruik: /watch {results[0].id}")
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /unwatch ───────────────────────────────────────────────────────────────

    @app_commands.command(
        name="unwatch",
        description="Verwijder een addon uit de watchlist."
    )
    @app_commands.describe(query="Addon naam of CurseForge project ID")
    async def unwatch(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)

        if query.strip().isdigit():
            removed = self.cache.watchlist_remove(guild_id, int(query.strip()))
            if removed:
                await interaction.followup.send(
                    f"✅ Addon `{query}` verwijderd uit watchlist.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Addon `{query}` niet gevonden in watchlist.", ephemeral=True
                )
        else:
            removed, name = self.cache.watchlist_remove_by_name(guild_id, query)
            if removed:
                await interaction.followup.send(
                    f"✅ **{name}** verwijderd uit watchlist.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Geen addon gevonden met naam `{query}` in watchlist.", ephemeral=True
                )

    # ── /watchlist ─────────────────────────────────────────────────────────────

    @app_commands.command(
        name="watchlist",
        description="Toon alle getrackte addons voor deze server."
    )
    async def show_watchlist(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        items    = self.cache.watchlist_get(guild_id)

        if not items:
            await interaction.followup.send(
                "📋 Watchlist is leeg. Gebruik `/watch <naam>` om addons toe te voegen.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📋 Watchlist — {len(items)} addon(s)",
            color=0x3d9eff
        )
        filter_labels = {
            "all":          "Alle releases",
            "stable":       "Alleen Stable",
            "stable_beta":  "Stable + Beta",
        }
        for item in items:
            embed.add_field(
                name=f"⚡ {item['addon_name']}",
                value=(
                    f"**Auteur:** {item['author_name'] or '–'}\n"
                    f"**ID:** `{item['addon_id']}`\n"
                    f"**Filter:** {filter_labels.get(item['release_filter'], item['release_filter'])}\n"
                    f"[CurseForge]({item['addon_url']})"
                ),
                inline=True
            )
        embed.set_footer(
            text=f"Max {MAX_WATCHLIST} addons · /watch <naam> om toe te voegen"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /search ────────────────────────────────────────────────────────────────

    @app_commands.command(
        name="search",
        description="Zoek WoW addons op CurseForge."
    )
    @app_commands.describe(query="Naam of auteur van de addon")
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        results = await self.cf.search_addons(query, limit=8)

        if not results:
            await interaction.followup.send(
                f"❌ Geen resultaten voor `{query}`.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🔍 Zoekresultaten voor '{query}'",
            description=f"{len(results)} gevonden — gebruik `/watch <ID>` om te tracken",
            color=0xa78bfa
        )
        guild_id = str(interaction.guild_id)
        for a in results:
            in_wl = self.cache.watchlist_exists(guild_id, a.id)
            embed.add_field(
                name=f"{'✅' if in_wl else '➕'} {a.name}",
                value=(
                    f"**Auteur:** {a.author_name}\n"
                    f"**ID:** `{a.id}`\n"
                    f"**Downloads:** {a.downloads:,}\n"
                    f"[CurseForge]({a.url})"
                ),
                inline=True
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _watch_embed(self, addon, release_filter: str, action: str) -> discord.Embed:
        filter_labels = {
            "all":         "Alle releases",
            "stable":      "Alleen Stable",
            "stable_beta": "Stable + Beta",
        }
        embed = discord.Embed(
            title=f"✅ {addon.name} {action}!",
            description=addon.summary or "",
            color=0x2ecc71,
            url=addon.url
        )
        embed.add_field(name="Auteur",   value=addon.author_name or "–")
        embed.add_field(name="Filter",   value=filter_labels.get(release_filter, release_filter))
        embed.add_field(name="Downloads",value=f"{addon.downloads:,}")
        if addon.logo_url:
            embed.set_thumbnail(url=addon.logo_url)
        embed.set_footer(text=f"ID: {addon.id} · /unwatch {addon.id} om te stoppen")
        return embed


async def setup(bot):
    await bot.add_cog(WatchlistCog(bot))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: watchlist.py │ v1.0.0 │ 2026-06-02                         ║
# ║  /watch /unwatch /watchlist /search slash commands                 ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
