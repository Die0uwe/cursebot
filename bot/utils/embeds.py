"""
CurseBot — utils/embeds.py
Discord embed builders — Slayer Alliance kleurschema.

Kleuren:
  🟢 Release : #00FF88  (neon groen)
  🟡 Beta    : #FFAA00  (goud-oranje)
  🔴 Alpha   : #FF3333  (rood)
  ℹ️ Info    : #00DFFF  (neon blauw — Slayer Alliance accent)
  ⚙️ System  : #BF00FF  (neon paars — Slayer Alliance primair)
"""
import discord
from datetime import datetime, timezone
from bot.models.release import AddonProject, AddonRelease


SLAYER_PURPLE = 0xBF00FF   # Primair accent
SLAYER_BLUE   = 0x00DFFF   # Secondair accent


def build_release_embed(
    project: AddonProject,
    release: AddonRelease,
    ai_summary: str | None = None,
) -> discord.Embed:
    """
    Bouwt de release-notificatie embed voor Discord.
    Gebruikt het Slayer Alliance kleurschema + release-type kleur.
    """
    color = release.release_type.color()
    label = release.release_type.label()

    embed = discord.Embed(
        title=f"{label}  —  {project.name}",
        url=project.url,
        color=color,
    )

    # Thumbnail: addon logo als beschikbaar
    if project.logo_url:
        embed.set_thumbnail(url=project.logo_url)

    # File info
    embed.add_field(
        name="📦 File",
        value=f"`{release.display_name}`",
        inline=True,
    )

    # Versies
    if release.game_versions:
        versions_str = ", ".join(sorted(release.game_versions)[:5])
        embed.add_field(name="🎮 Game Versions", value=versions_str, inline=True)

    # Downloads
    if project.downloads:
        embed.add_field(
            name="⬇️ Total Downloads",
            value=f"{project.downloads:,}",
            inline=True,
        )

    # Changelog — AI samenvatting als beschikbaar, anders raw
    if ai_summary:
        embed.add_field(
            name="✨ Changelog (AI Summary)",
            value=ai_summary[:1024],
            inline=False,
        )
    elif release.changelog:
        embed.add_field(
            name="📝 Changelog",
            value=release.short_changelog(400),
            inline=False,
        )

    # Download link
    if release.download_url:
        embed.add_field(
            name="🔗 Direct Download",
            value=f"[Download]({release.download_url})",
            inline=True,
        )

    # Project link
    embed.add_field(
        name="🌐 CurseForge",
        value=f"[Bekijk project]({project.url})",
        inline=True,
    )

    # Footer + timestamp
    upload_time = release.uploaded_at or datetime.now(timezone.utc)
    embed.set_footer(text="CurseBot · DieOuwe Slayer Alliance Edition")
    embed.timestamp = upload_time

    return embed


def build_status_embed(
    projects: list[AddonProject],
    interval_minutes: int,
) -> discord.Embed:
    """Status-embed voor het /status slash command."""
    embed = discord.Embed(
        title="⚙️ CurseBot — Monitor Status",
        color=SLAYER_PURPLE,
    )
    embed.add_field(
        name="📡 Tracked Addons",
        value=str(len(projects)),
        inline=True,
    )
    embed.add_field(
        name="⏱️ Poll Interval",
        value=f"Every {interval_minutes} min",
        inline=True,
    )
    if projects:
        project_list = "\n".join(
            f"• [{p.name}]({p.url}) — {p.downloads:,} downloads"
            for p in projects[:15]
        )
        embed.add_field(name="📦 Projects", value=project_list, inline=False)

    embed.set_footer(text="CurseBot · Slayer Alliance Edition")
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def build_error_embed(title: str, description: str) -> discord.Embed:
    """Fout-embed voor interne bot errors (alleen zichtbaar in log-channel)."""
    embed = discord.Embed(title=f"❌ {title}", description=description, color=0xFF0000)
    embed.set_footer(text="CurseBot Error")
    embed.timestamp = datetime.now(timezone.utc)
    return embed
