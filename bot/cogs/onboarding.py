# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — cogs/onboarding.py  v1.0.0

Onboarding flow bij guild join:
  1. Bot joint server → stuurt welkomstbericht naar system channel of eerste kanaal
  2. Admin kiest release kanaal via dropdown
  3. Bot bevestigt setup en toont alle slash commands
  4. /setup command voor re-onboarding als iets fout ging
  5. /invite command voor de invite link met juiste permissions
"""
import discord
from discord.ext import commands
from discord import app_commands
from bot.services.cache import CacheService
from bot.services.stats import STATS
from bot.utils.logger import get_logger

log = get_logger(__name__)

# Permission integer voor de invite URL
REQUIRED_PERMISSIONS = discord.Permissions(
    view_channel=True,
    send_messages=True,
    send_messages_in_threads=True,
    embed_links=True,
    add_reactions=True,
    use_external_emojis=True,
    read_message_history=True,
    manage_messages=True,
)

PERMISSION_INT = REQUIRED_PERMISSIONS.value


class ChannelSelectView(discord.ui.View):
    """
    Interactieve view met kanaal-selector en release type knoppen.
    Verschijnt als de bot een nieuwe server joint.
    """
    def __init__(self, cache: CacheService, guild: discord.Guild):
        super().__init__(timeout=300)  # 5 minuten
        self.cache   = cache
        self.guild   = guild
        self._done   = False

        # Voeg kanaal select menu toe
        self.add_item(ChannelSelect(cache, guild))

    async def on_timeout(self):
        if not self._done:
            log.warning(f"[ONBOARD] Setup timeout voor guild {self.guild.id}")


class ChannelSelect(discord.ui.ChannelSelect):
    """Dropdown voor kanaal selectie."""
    def __init__(self, cache: CacheService, guild: discord.Guild):
        super().__init__(
            placeholder="📢 Kies het kanaal voor release notificaties...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
        )
        self.cache = cache
        self.guild = guild

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]

        # Controleer of bot berichten kan sturen in het gekozen kanaal
        perms = channel.permissions_for(self.guild.me)
        if not perms.send_messages or not perms.embed_links:
            await interaction.response.send_message(
                f"❌ Ik heb geen rechten in {channel.mention}!\n"
                f"Geef me **Berichten sturen** en **Links insluiten** rechten daar.",
                ephemeral=True
            )
            return

        # Sla kanaal op als 'all' type
        self.cache.channel_set(str(self.guild.id), "all", channel.id)
        STATS.add_log(f"[ONBOARD] Guild {self.guild.name} → #{channel.name}")

        # Stuur bevestiging
        embed = discord.Embed(
            title="✅ CurseBot is klaar!",
            description=(
                f"Release notificaties worden gestuurd naar {channel.mention}.\n\n"
                f"**Wil je aparte kanalen per release type?**\n"
                f"Gebruik `/setchannel` om extra kanalen te configureren:\n"
                f"```\n"
                f"/setchannel #stable-releases  release_type: Stable\n"
                f"/setchannel #beta-releases    release_type: Beta\n"
                f"```"
            ),
            color=0x2ecc71
        )
        embed.add_field(
            name="📋 Beschikbare commands",
            value=(
                "`/watch`        — addon toevoegen op naam of ID\n"
                "`/unwatch`      — addon verwijderen\n"
                "`/watchlist`    — getrackte addons bekijken\n"
                "`/search`       — addons zoeken op CurseForge\n"
                "`/setchannel`   — kanaal per release type instellen\n"
                "`/stats`        — download statistieken\n"
                "`/status`       — bot status\n"
                "`/check`        — directe CF check starten\n"
                "`/reset`        — file cache wissen"
            ),
            inline=False
        )
        embed.add_field(
            name="🔗 Links",
            value=(
                "[CurseForge](https://www.curseforge.com/wow/search?search=DIEOUWE) · "
                "[Discord](https://discord.gg/y8Pu5qsEbQ) · "
                "[dieouwe.nl](https://www.dieouwe.nl) · "
                "[GitHub](https://github.com/Die0uwe/cursebot)"
            ),
            inline=False
        )
        embed.set_footer(text="CurseBot · Slayer Alliance Edition · v2.0")

        # Stuur een test bericht naar het gekozen kanaal
        try:
            test_embed = discord.Embed(
                title="⚡ CurseBot is hier!",
                description=(
                    "Dit kanaal ontvangt voortaan WoW addon release notificaties.\n"
                    f"Getrackte auteur: **dieouwe** · "
                    f"Gebruik `/watch <naam>` om meer addons te tracken."
                ),
                color=0xf5a623
            )
            test_embed.set_footer(text="CurseBot · Slayer Alliance Edition")
            await channel.send(embed=test_embed)
        except discord.Forbidden:
            pass

        # Disable de view
        self.view._done = True
        for item in self.view.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self.view)


class OnboardingCog(commands.Cog, name="Onboarding"):
    def __init__(self, bot):
        self.bot   = bot
        self.cache = CacheService(bot.settings.database_path)

    # ── Guild join event ────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        log.info(f"[ONBOARD] Bot heeft guild '{guild.name}' ({guild.id}) gejoind")
        STATS.add_log(f"[ONBOARD] Nieuw: {guild.name} ({guild.member_count} leden)")
        STATS.guilds = len(self.bot.guilds)

        # Zoek het beste kanaal om het welkomstbericht te sturen
        target = self._find_best_channel(guild)
        if not target:
            log.warning(f"[ONBOARD] Geen bruikbaar kanaal gevonden in {guild.name}")
            return

        embed = discord.Embed(
            title="⚡ Hallo! Ik ben CurseBot",
            description=(
                "Ik monitor WoW addon releases op CurseForge en stuur "
                "notificaties zodra er een nieuwe versie uitkomt.\n\n"
                "**Kies hieronder het kanaal voor release notificaties.**\n"
                "Alleen admins kunnen dit instellen."
            ),
            color=0xf5a623
        )
        embed.add_field(
            name="✅ Wat ik doe",
            value=(
                "• Nieuwe addon releases detecteren\n"
                "• Discord embed sturen met changelog\n"
                "• Meerdere auteurs en addons tracken\n"
                "• Aparte kanalen per release type"
            ),
            inline=True
        )
        embed.add_field(
            name="⚙️ Benodigde rechten",
            value=(
                "• Berichten sturen\n"
                "• Links insluiten\n"
                "• Berichten lezen\n"
                "• Externe emoji's"
            ),
            inline=True
        )
        embed.set_footer(
            text="CurseBot · Slayer Alliance Edition · Selecteer een kanaal om te beginnen"
        )

        view = ChannelSelectView(self.cache, guild)
        try:
            await target.send(embed=embed, view=view)
        except discord.Forbidden:
            log.warning(f"[ONBOARD] Geen rechten om bericht te sturen in {guild.name}")

    def _find_best_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Zoek het beste kanaal voor het welkomstbericht."""
        me = guild.me

        # Voorkeur 1: system channel (standaard Discord welkomst kanaal)
        if guild.system_channel:
            perms = guild.system_channel.permissions_for(me)
            if perms.send_messages and perms.embed_links:
                return guild.system_channel

        # Voorkeur 2: kanaal met 'general', 'algemeen', 'bot' in de naam
        for keyword in ["general", "algemeen", "bots", "bot", "commands"]:
            for ch in guild.text_channels:
                if keyword in ch.name.lower():
                    perms = ch.permissions_for(me)
                    if perms.send_messages and perms.embed_links:
                        return ch

        # Fallback: eerste kanaal waar we mogen schrijven
        for ch in guild.text_channels:
            perms = ch.permissions_for(me)
            if perms.send_messages and perms.embed_links:
                return ch

        return None

    # ── Guild remove event ──────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        log.info(f"[ONBOARD] Bot verliet guild '{guild.name}' ({guild.id})")
        STATS.add_log(f"[ONBOARD] Verlaten: {guild.name}")
        STATS.guilds = len(self.bot.guilds)

    # ── /setup command ──────────────────────────────────────────────────────────
    @app_commands.command(
        name="setup",
        description="Herstart de CurseBot setup — kies opnieuw je notificatiekanaal."
    )
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Re-onboarding voor als de initiële setup gemist werd."""
        embed = discord.Embed(
            title="⚡ CurseBot Setup",
            description=(
                "Kies het kanaal voor release notificaties.\n"
                "Gebruik `/setchannel` daarna voor aparte kanalen per release type."
            ),
            color=0xf5a623
        )

        # Toon huidige configuratie als die er al is
        channels = self.cache.channel_list(str(interaction.guild_id))
        if channels:
            ch_lines = []
            for c in channels:
                ch_obj = self.bot.get_channel(c["channel_id"])
                ch_name = ch_obj.mention if ch_obj else f"<#{c['channel_id']}>"
                ch_lines.append(f"`{c['channel_type']}` → {ch_name}")
            embed.add_field(
                name="Huidige configuratie",
                value="\n".join(ch_lines),
                inline=False
            )

        view = ChannelSelectView(self.cache, interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ── /invite command ─────────────────────────────────────────────────────────
    @app_commands.command(
        name="invite",
        description="Genereer een invite link om CurseBot toe te voegen aan een andere server."
    )
    async def invite(self, interaction: discord.Interaction):
        client_id  = self.bot.user.id
        invite_url = (
            f"https://discord.com/oauth2/authorize"
            f"?client_id={client_id}"
            f"&permissions={PERMISSION_INT}"
            f"&scope=bot+applications.commands"
        )

        embed = discord.Embed(
            title="⚡ CurseBot toevoegen",
            description=(
                f"Klik hieronder om CurseBot toe te voegen aan een server.\n\n"
                f"**Benodigde rechten:**\n"
                f"✅ Kanalen bekijken\n"
                f"✅ Berichten sturen\n"
                f"✅ Links insluiten\n"
                f"✅ Externe emoji's gebruiken\n"
                f"✅ Berichten lezen\n"
                f"✅ Reacties toevoegen\n"
                f"✅ Berichten beheren"
            ),
            color=0xf5a623,
            url=invite_url
        )
        embed.add_field(
            name="🔗 Invite link",
            value=f"[Klik hier om CurseBot toe te voegen]({invite_url})",
            inline=False
        )
        embed.set_footer(
            text=f"Permission integer: {PERMISSION_INT}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /permissions command ────────────────────────────────────────────────────
    @app_commands.command(
        name="permissions",
        description="Controleer of CurseBot de juiste rechten heeft in dit kanaal."
    )
    @app_commands.describe(channel="Het kanaal om te controleren (leeg = huidig kanaal)")
    async def check_permissions(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None
    ):
        ch    = channel or interaction.channel
        perms = ch.permissions_for(interaction.guild.me)

        checks = [
            ("Kanaal bekijken",         perms.view_channel),
            ("Berichten sturen",        perms.send_messages),
            ("Berichten in threads",    perms.send_messages_in_threads),
            ("Links insluiten",         perms.embed_links),
            ("Reacties toevoegen",      perms.add_reactions),
            ("Externe emoji's",         perms.use_external_emojis),
            ("Berichten lezen",         perms.read_message_history),
            ("Berichten beheren",       perms.manage_messages),
        ]

        all_ok = all(ok for _, ok in checks)
        embed  = discord.Embed(
            title=f"{'✅' if all_ok else '⚠️'} Rechten in #{ch.name}",
            color=0x2ecc71 if all_ok else 0xf5a623,
            description="✅ = heeft recht · ❌ = mist recht"
        )

        lines = [
            f"{'✅' if ok else '❌'} {name}"
            for name, ok in checks
        ]
        embed.add_field(name="Rechten", value="\n".join(lines), inline=False)

        if not all_ok:
            missing = [name for name, ok in checks if not ok]
            embed.add_field(
                name="❌ Ontbrekende rechten",
                value="\n".join(f"• {m}" for m in missing),
                inline=False
            )
            embed.set_footer(text="Geef me de ontbrekende rechten via Serverinstellingen → Rollen")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(OnboardingCog(bot))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: onboarding.py │ v1.0.0 │ 2026-06-02                        ║
# ║  Guild join flow · kanaal selector · /setup /invite /permissions   ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
