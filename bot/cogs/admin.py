# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — cogs/admin.py  v2.0.0
Admin slash commands + channel configuratie.
"""
import discord
from discord.ext import commands
from discord import app_commands
from bot.services.cache import CacheService
from bot.utils.embeds import build_status_embed, build_error_embed
from bot.utils.logger import get_logger
from bot.services.stats import STATS

log = get_logger(__name__)


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(
            "❌ Alleen admins kunnen dit gebruiken.", ephemeral=True
        )
        return False
    return app_commands.check(predicate)


class AdminCog(commands.Cog, name="Admin"):

    def __init__(self, bot):
        self.bot   = bot
        self.cache = CacheService(bot.settings.database_path)

    def _get_cf_cog(self):
        return self.bot.cogs.get("CurseForge Monitor")

    # ── /status ────────────────────────────────────────────────────────────────
    @app_commands.command(name="status", description="Toon CurseBot monitor status.")
    @is_admin()
    async def status(self, interaction: discord.Interaction):
        cf       = self._get_cf_cog()
        projects = cf.known_projects if cf else []
        embed    = build_status_embed(projects, self.bot.settings.check_interval_minutes)

        # Voeg channel config toe
        channels = self.cache.channel_list(str(interaction.guild_id))
        if channels:
            ch_lines = []
            for c in channels:
                ch_obj = self.bot.get_channel(c["channel_id"])
                ch_name = ch_obj.mention if ch_obj else f"#{c['channel_id']}"
                ch_lines.append(f"`{c['channel_type']}` → {ch_name}")
            embed.add_field(
                name="📢 Kanaalconfiguratie",
                value="\n".join(ch_lines),
                inline=False
            )

        # Watchlist stats
        wl = self.cache.watchlist_all()
        guild_wl = [x for x in wl if x["guild_id"] == str(interaction.guild_id)]
        embed.add_field(
            name="📋 Watchlist",
            value=f"{len(guild_wl)} addons getrackt",
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /check ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="check", description="Forceer onmiddellijke CurseForge check.")
    @is_admin()
    async def force_check(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cf = self._get_cf_cog()
        if not cf:
            await interaction.followup.send("❌ CurseForge cog niet geladen.", ephemeral=True)
            return
        STATS.force_check = True
        await interaction.followup.send("✅ CF check getriggerd.", ephemeral=True)

    # ── /projects ──────────────────────────────────────────────────────────────
    @app_commands.command(name="projects", description="Toon alle getrackte CurseForge projecten.")
    @is_admin()
    async def projects(self, interaction: discord.Interaction):
        cf = self._get_cf_cog()
        if not cf or not cf.known_projects:
            await interaction.response.send_message("⚠️ Geen projecten geladen.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"📦 Projecten — {len(cf.known_projects)} addons",
            color=0x3d9eff
        )
        for p in cf.known_projects:
            growth = self.cache.stats_growth(p.id)
            growth_str = f" (+{growth:,})" if growth > 0 else ""
            embed.add_field(
                name=p.name,
                value=f"[CurseForge]({p.url})\n`{p.downloads:,} dl{growth_str}`",
                inline=True
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /reset ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="reset", description="Reset de file ID cache.")
    @is_admin()
    async def reset_cache(self, interaction: discord.Interaction):
        self.cache.wipe()
        STATS.add_log(f"[ADMIN] Cache gereset door {interaction.user}")
        await interaction.response.send_message("✅ Cache gewist.", ephemeral=True)

    # ── /setchannel ────────────────────────────────────────────────────────────
    @app_commands.command(
        name="setchannel",
        description="Stel een kanaal in voor release notificaties per type."
    )
    @app_commands.describe(
        channel="Het Discord kanaal voor notificaties",
        release_type="Welk type releases naar dit kanaal sturen?"
    )
    @app_commands.choices(release_type=[
        app_commands.Choice(name="Alle releases (standaard)", value="all"),
        app_commands.Choice(name="Alleen Stable releases",    value="stable"),
        app_commands.Choice(name="Alleen Beta releases",      value="beta"),
        app_commands.Choice(name="Alleen Alpha releases",     value="alpha"),
    ])
    @is_admin()
    async def setchannel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        release_type: app_commands.Choice[str] | None = None,
    ):
        ch_type = release_type.value if release_type else "all"
        self.cache.channel_set(str(interaction.guild_id), ch_type, channel.id)

        type_labels = {
            "all":    "alle releases",
            "stable": "Stable releases",
            "beta":   "Beta releases",
            "alpha":  "Alpha releases",
        }
        STATS.add_log(f"[ADMIN] Channel config: {ch_type} → #{channel.name}")
        embed = discord.Embed(
            title="📢 Kanaal ingesteld",
            description=(
                f"{channel.mention} ontvangt voortaan **{type_labels[ch_type]}**.\n\n"
                f"Gebruik `/setchannel` opnieuw om meer kanalen te configureren.\n"
                f"Gebruik `/status` om de volledige configuratie te zien."
            ),
            color=0x2ecc71
        )
        embed.add_field(name="Type",   value=type_labels[ch_type])
        embed.add_field(name="Kanaal", value=channel.mention)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /removechannel ─────────────────────────────────────────────────────────
    @app_commands.command(
        name="removechannel",
        description="Verwijder een kanaalconfiguratie."
    )
    @app_commands.choices(release_type=[
        app_commands.Choice(name="Alle releases", value="all"),
        app_commands.Choice(name="Stable",        value="stable"),
        app_commands.Choice(name="Beta",          value="beta"),
        app_commands.Choice(name="Alpha",         value="alpha"),
    ])
    @is_admin()
    async def removechannel(
        self,
        interaction: discord.Interaction,
        release_type: app_commands.Choice[str],
    ):
        removed = self.cache.channel_remove(
            str(interaction.guild_id), release_type.value
        )
        if removed:
            await interaction.response.send_message(
                f"✅ Kanaalconfiguratie voor `{release_type.value}` verwijderd.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Geen configuratie gevonden voor `{release_type.value}`.",
                ephemeral=True
            )

    # ── /stats ─────────────────────────────────────────────────────────────────
    @app_commands.command(
        name="stats",
        description="Toon download statistieken voor getrackte addons."
    )
    @is_admin()
    async def stats_cmd(self, interaction: discord.Interaction):
        totals = self.cache.stats_all_totals()
        if not totals:
            await interaction.response.send_message(
                "ℹ️ Nog geen statistieken opgeslagen. Even wachten na de volgende CF check.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📊 Download statistieken",
            color=0xa78bfa,
            description="Groei = verschil t.o.v. vorige meting"
        )
        for row in totals[:12]:
            growth = self.cache.stats_growth(row["addon_id"])
            meta   = self.cache.addon_meta_get(row["addon_id"])
            name   = meta["name"] if meta else f"Addon #{row['addon_id']}"
            growth_str = (
                f"▲ +{growth:,}" if growth > 0 else
                f"▼ {growth:,}" if growth < 0 else "–"
            )
            embed.add_field(
                name=name,
                value=f"`{row['downloads']:,} downloads`\n{growth_str}",
                inline=True
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: admin.py │ v2.0.0 │ 2026-06-02                             ║
# ║  /setchannel /removechannel /stats + multi-channel support         ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
