# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — bot/cogs/curseforge.py  v3.0.0

Monitor loop die elke X minuten CurseForge pollt en Discord embeds stuurt
bij nieuwe releases. Werkt voor zowel eigen addons (auteur-slug) als
watchlist-addons (per guild).

CHANGES v3.0.0:
  - Volledige addon update detectie — ook voor watchlist addons van andere auteurs
  - release_history tabel integratie — persistente log van alle gestuurd notificaties
  - Multi-guild notificaties via channel_config (per release type)
  - WAF backoff: Cloudfront 403 detectie met exponentieel wachten
  - STATS tellers: releases_detected, last_check, next_check
  - Graceful degradation: één falende addon stopt de loop niet
  - /check force support via STATS.force_check flag
"""
import asyncio
import time
from datetime import datetime, timezone

import discord
import httpx
from discord.ext import commands, tasks

from bot.services.cache import CacheService
from bot.services.curseforge_api import CurseForgeService
from bot.services.stats import STATS
from bot.utils.logger import get_logger

log = get_logger(__name__)

# ── WAF Backoff tijden (seconden) ──────────────────────────────────────────────
_WAF_BACKOFF_STEPS = [60, 300, 3600]   # 1m → 5m → 1u
_WAF_MAX_STEP      = len(_WAF_BACKOFF_STEPS) - 1

# Release type → kleur voor Discord embed
_RELEASE_COLORS = {
    1: 0x00C853,   # Stable  → groen
    2: 0xFFB300,   # Beta    → amber
    3: 0xFF5252,   # Alpha   → rood
}
_RELEASE_LABELS = {1: "Stable", 2: "Beta", 3: "Alpha"}


def _build_embed(
    addon_name:   str,
    addon_url:    str,
    logo_url:     str | None,
    file_name:    str,
    display_name: str,
    release_type: int,
    game_versions: list[str],
    changelog:    str,
    downloads:    int,
    author_name:  str = "",
    summary:      str = "",
) -> discord.Embed:
    """Bouw een Discord embed voor een nieuwe addon release."""
    label  = _RELEASE_LABELS.get(release_type, "Release")
    color  = _RELEASE_COLORS.get(release_type, 0x7289DA)
    prefix = {"Stable": "✅", "Beta": "🔶", "Alpha": "🔴"}.get(label, "📦")

    embed = discord.Embed(
        title       = f"{prefix} {addon_name} — Nieuwe {label}!",
        url         = addon_url or "",
        description = summary[:100] if summary else "",
        color       = color,
        timestamp   = datetime.now(timezone.utc),
    )

    if logo_url:
        embed.set_thumbnail(url=logo_url)

    embed.add_field(name="📁 Bestand",        value=f"`{display_name or file_name}`", inline=True)
    embed.add_field(name="🏷️ Type",           value=label,                            inline=True)

    if game_versions:
        versions_str = ", ".join(sorted(game_versions, reverse=True)[:4])
        embed.add_field(name="🎮 Game versies", value=versions_str, inline=True)

    if author_name:
        embed.add_field(name="👤 Auteur",       value=author_name, inline=True)

    if downloads:
        dl_str = f"{downloads:,}".replace(",", ".")
        embed.add_field(name="⬇️ Downloads",   value=dl_str, inline=True)

    if changelog:
        # Max 900 tekens voor het changelog veld
        cl = changelog[:900]
        if len(changelog) > 900:
            cl += "\n…"
        embed.add_field(name="📋 Changelog", value=cl, inline=False)

    embed.set_footer(text="CurseBot · Slayer Alliance Edition")
    return embed


class CurseForgeCog(commands.Cog):
    """
    Centrale monitor cog. Pollt CurseForge voor:
      - Eigen addons (auteur-slug discovery)
      - Watchlist addons (per guild, elke addon_id)

    Per check:
      1. Haal eigen projecten op (discovery)
      2. Voeg watchlist toe (dedupliceerd)
      3. Per project: haal latest file op
      4. Vergelijk met file_cache
      5. Nieuw → embed sturen → history opslaan → cache bijwerken
    """

    def __init__(self, bot: commands.Bot):
        self.bot          = bot
        self.settings     = bot.settings
        self._cf          = CurseForgeService(
            api_key   = self.settings.curseforge_api_key,
            game_id   = self.settings.cf_game_id,
            author_id = self.settings.cf_author_id,
        )
        self._cache       = CacheService(self.settings.database_path)
        self._waf_step    = 0          # huidige WAF backoff stap (index in _WAF_BACKOFF_STEPS)
        self._waf_until   = 0.0        # timestamp tot wanneer we wachten
        self._known_ids:  set[int] = set()  # eigen project IDs (discovery resultaat)
        self.monitor_loop.start()

    def cog_unload(self):
        self.monitor_loop.cancel()
        log.info("[CF] Monitor loop gestopt")

    # ─────────────────────────────────────────────────────────────────────────
    # MONITOR LOOP
    # ─────────────────────────────────────────────────────────────────────────

    @tasks.loop(minutes=1)
    async def monitor_loop(self):
        """
        Draait elke minuut. Voert daadwerkelijke check uit na interval
        of als STATS.force_check gezet is.
        """
        # ── WAF backoff actief? ────────────────────────────────────────────
        if self._waf_until and time.time() < self._waf_until:
            remaining = int(self._waf_until - time.time())
            STATS.add_log(f"[CF] WAF backoff actief — nog {remaining}s wachten")
            return

        # ── Interval check ─────────────────────────────────────────────────
        interval_secs = self.settings.check_interval_minutes * 60
        now           = time.time()

        if not STATS.force_check:
            last = getattr(self, "_last_check_ts", 0)
            if now - last < interval_secs:
                # Volgende check updaten voor dashboard
                next_ts = last + interval_secs
                STATS.next_check = datetime.fromtimestamp(
                    next_ts, tz=timezone.utc
                ).strftime("%H:%M:%S UTC")
                return

        # Reset force flag
        if STATS.force_check:
            STATS.force_check = False
            log.info("[CF] Handmatige check getriggerd")
            STATS.add_log("[CF] Handmatige check gestart")

        self._last_check_ts = now
        STATS.last_check    = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        next_ts             = now + interval_secs
        STATS.next_check    = datetime.fromtimestamp(
            next_ts, tz=timezone.utc
        ).strftime("%H:%M:%S UTC")

        await self._run_check()

    @monitor_loop.before_loop
    async def before_monitor(self):
        await self.bot.wait_until_ready()
        log.info(f"[CF] Monitor loop actief — interval: {self.settings.check_interval_minutes}m")
        STATS.add_log(f"[CF] Monitor gestart (interval={self.settings.check_interval_minutes}m)")

    @monitor_loop.error
    async def monitor_error(self, error: Exception):
        """Loop stopt NIET bij fout — logt en gaat door."""
        log.error(f"[CF] Monitor loop fout: {error}", exc_info=True)
        STATS.add_log(f"[CF] Loop fout: {error}")

    # ─────────────────────────────────────────────────────────────────────────
    # KERN CHECK LOGICA
    # ─────────────────────────────────────────────────────────────────────────

    async def _run_check(self):
        """Voer één volledige check uit over alle te monitoren addons."""
        log.info("[CF] Check gestart")
        STATS.add_log("[CF] Check gestart")

        # Stap 1 — Eigen addons discovery
        own_projects = await self._discover_own_projects()

        # Stap 2 — Bouw gecombineerde project-set
        # { addon_id: { name, slug, url, logo_url, downloads, author_name, summary } }
        all_projects = {p.id: p for p in own_projects}

        # Stap 3 — Voeg watchlist toe (alle guilds, dedupliceer op addon_id)
        watchlist_projects = await self._load_watchlist_projects(
            exclude_ids=set(all_projects.keys())
        )
        all_projects.update(watchlist_projects)

        STATS.projects_tracked = len(all_projects)
        STATS.project_list     = [
            {
                "id":          p.id,
                "name":        p.name,
                "slug":        p.slug,
                "url":         p.url,
                "downloads":   p.downloads,
                "logo_url":    p.logo_url,
                "summary":     p.summary,
                "author_name": getattr(p, "author_name", ""),
            }
            for p in all_projects.values()
        ]

        if not all_projects:
            log.warning("[CF] Geen projecten gevonden — check CF_AUTHOR_SLUG en watchlist")
            STATS.add_log("[CF] ⚠ Geen projecten gevonden")
            return

        log.info(f"[CF] {len(all_projects)} projecten te checken")

        # Stap 4 — Per project: check op nieuwe release
        new_count = 0
        for project in all_projects.values():
            try:
                found = await self._check_project(project)
                if found:
                    new_count += 1
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    await self._handle_waf(e)
                    break  # Stop de check bij WAF blokkade
                log.error(f"[CF] HTTP fout voor {project.name}: {e}")
                STATS.add_log(f"[CF] HTTP fout {project.name}: {e.response.status_code}")
            except Exception as e:
                log.error(f"[CF] Fout bij {project.name}: {e}", exc_info=True)
                STATS.add_log(f"[CF] Fout {project.name}: {e}")

        # WAF reset bij succesvolle check
        if self._waf_step > 0:
            log.info("[CF] WAF backoff reset — checks succesvol")
            self._waf_step  = 0
            self._waf_until = 0.0

        msg = f"[CF] Check klaar — {new_count} nieuwe release(s) van {len(all_projects)} addons"
        log.info(msg)
        STATS.add_log(msg)

    async def _discover_own_projects(self):
        """Haal eigen addons op via auteur-slug discovery."""
        try:
            projects = await self._cf.get_author_projects(self.settings.cf_author_slug)
            self._known_ids = {p.id for p in projects}
            STATS.add_log(f"[CF] {len(projects)} eigen addons gevonden")
            return projects
        except Exception as e:
            log.error(f"[CF] Discovery mislukt: {e}")
            STATS.add_log(f"[CF] Discovery mislukt: {e}")
            return []

    async def _load_watchlist_projects(self, exclude_ids: set[int]) -> dict:
        """
        Laad alle watchlist-addons van alle guilds.
        Haalt metadata op via CF API als niet gecacht.
        """
        result       = {}
        watchlist    = self._cache.watchlist_all()
        unique_ids   = {
            item["addon_id"]
            for item in watchlist
            if item["addon_id"] not in exclude_ids
        }

        for addon_id in unique_ids:
            # Probeer eerst gecachte metadata
            meta = self._cache.addon_meta_get(addon_id)
            if meta:
                # Bouw een minimaal project-object van dict
                result[addon_id] = _DictProject(meta)
                continue

            # Haal live op van CF API
            try:
                project = await self._cf.get_addon_by_id(addon_id)
                if project:
                    self._cache.addon_meta_set(addon_id, {
                        "name":        project.name,
                        "slug":        project.slug,
                        "author_name": getattr(project, "author_name", ""),
                        "summary":     project.summary,
                        "url":         project.url,
                        "logo_url":    project.logo_url,
                        "downloads":   project.downloads,
                    })
                    result[addon_id] = project
            except Exception as e:
                log.warning(f"[CF] Watchlist addon {addon_id} ophalen mislukt: {e}")

        if unique_ids:
            STATS.add_log(f"[CF] {len(result)} watchlist addons geladen")

        STATS.watchlist_count = len(watchlist)
        return result

    async def _check_project(self, project) -> bool:
        """
        Check één project op een nieuwe release.
        Geeft True terug als een nieuwe release gedetecteerd en verstuurd is.
        """
        cache_key = f"cf:{project.id}:file_id"
        release   = await self._cf.get_latest_file(project.id)

        if not release:
            return False

        # Opslaan van download stats (trend analyse)
        self._cache.stats_record(project.id, project.downloads)

        # Vergelijk file_id met cache
        cached_id = self._cache.get(cache_key)
        if cached_id and int(cached_id) == release.file_id:
            return False  # Geen nieuwe release

        # ── NIEUWE RELEASE GEDETECTEERD ────────────────────────────────────
        is_first_run = cached_id is None
        old_id       = cached_id

        # Cache bijwerken vóór notificaties (voorkomt dubbele embeds bij herstart)
        self._cache.set(cache_key, str(release.file_id))

        if is_first_run:
            # Eerste keer zien — geen notificatie, alleen cachen
            log.info(f"[CF] {project.name} — eerste registratie file_id={release.file_id}")
            STATS.add_log(f"[CF] {project.name} — eerste registratie (geen embed)")
            return False

        log.info(
            f"[CF] 🆕 {project.name} — nieuw bestand! "
            f"{old_id} → {release.file_id} ({_RELEASE_LABELS.get(release.release_type.value, '?')})"
        )
        STATS.releases_detected += 1
        STATS.add_log(
            f"[CF] 🆕 {project.name} v{release.display_name} "
            f"({_RELEASE_LABELS.get(release.release_type.value, '?')})"
        )

        # AI changelog samenvatting (optioneel)
        changelog = release.changelog or ""
        if (
            self.settings.summarize_changelogs
            and self.settings.anthropic_api_key
            and changelog
        ):
            try:
                from bot.services.claude_api import ClaudeService
                claude    = ClaudeService(self.settings.anthropic_api_key)
                summary   = await claude.summarize_changelog(project.name, changelog)
                if summary:
                    changelog = summary
            except Exception as e:
                log.debug(f"[CF] Claude samenvatting mislukt: {e}")

        # Embed bouwen
        embed = _build_embed(
            addon_name    = project.name,
            addon_url     = project.url,
            logo_url      = project.logo_url,
            file_name     = release.file_name,
            display_name  = release.display_name,
            release_type  = release.release_type.value,
            game_versions = release.game_versions,
            changelog     = changelog,
            downloads     = project.downloads,
            author_name   = getattr(project, "author_name", ""),
            summary       = project.summary,
        )

        # Notificaties sturen naar alle relevante kanalen
        await self._send_notifications(project, release, embed)

        # Release history opslaan
        self._cache.release_history_add(
            addon_id     = project.id,
            addon_name   = project.name,
            file_id      = release.file_id,
            display_name = release.display_name,
            release_type = _RELEASE_LABELS.get(release.release_type.value, "?"),
        )

        return True

    async def _send_notifications(self, project, release, embed: discord.Embed):
        """
        Stuur embed naar alle geconfigureerde kanalen voor alle guilds.
        Respecteert release_filter per watchlist item en channel_type config.
        """
        release_label = _RELEASE_LABELS.get(release.release_type.value, "stable").lower()
        sent_to       = []

        for guild in self.bot.guilds:
            guild_id = str(guild.id)

            # Bepaal of dit een eigen addon is of watchlist-only
            is_own_addon  = project.id in self._known_ids
            wl_item       = self._get_watchlist_item(guild_id, project.id)

            # Addon is niet van ons én niet op watchlist van deze guild → skip
            if not is_own_addon and not wl_item:
                continue

            # Controleer watchlist release filter
            if wl_item:
                wl_filter = wl_item.get("release_filter", "all")
                if not _passes_filter(release_label, wl_filter):
                    log.debug(
                        f"[CF] {project.name} gefilterd voor guild {guild_id} "
                        f"(filter={wl_filter}, type={release_label})"
                    )
                    continue

            # Haal channel op (specifiek type → fallback naar 'all')
            channel_id = self._cache.channel_get(guild_id, release_label)
            if not channel_id:
                channel_id = self._cache.channel_get(guild_id, "all")
            if not channel_id:
                # Fallback: gebruik RELEASE_CHANNEL_ID uit .env
                channel_id = self.settings.release_channel_id

            channel = self.bot.get_channel(channel_id)
            if not channel:
                log.warning(f"[CF] Kanaal {channel_id} niet gevonden voor guild {guild_id}")
                STATS.add_log(f"[CF] ⚠ Kanaal {channel_id} niet gevonden")
                continue

            try:
                await channel.send(embed=embed)
                sent_to.append(f"{guild.name}#{channel.name}")
                log.info(f"[CF] Embed verstuurd → {guild.name}#{channel.name}")
            except discord.Forbidden:
                log.warning(f"[CF] Geen schrijfrechten in {guild.name}#{channel.name}")
                STATS.add_log(f"[CF] ⚠ Geen rechten: {guild.name}#{channel.name}")
            except Exception as e:
                log.error(f"[CF] Sturen mislukt ({guild.name}): {e}")

        if sent_to:
            STATS.add_log(f"[CF] Embed verstuurd naar: {', '.join(sent_to)}")

    def _get_watchlist_item(self, guild_id: str, addon_id: int) -> dict | None:
        """Haal watchlist item op voor een specifieke guild + addon combinatie."""
        items = self._cache.watchlist_get(guild_id)
        for item in items:
            if item["addon_id"] == addon_id:
                return item
        return None

    async def _handle_waf(self, error: httpx.HTTPStatusError):
        """
        Verwerk een CF 403 WAF blokkade.
        Verhoog backoff stap en stel wacht-timer in.
        """
        wait = _WAF_BACKOFF_STEPS[min(self._waf_step, _WAF_MAX_STEP)]
        self._waf_until = time.time() + wait
        msg = (
            f"[CF] ⛔ WAF blokkade (403) — wacht {wait}s "
            f"(stap {self._waf_step + 1}/{_WAF_MAX_STEP + 1})"
        )
        log.warning(msg)
        STATS.add_log(msg)
        if self._waf_step < _WAF_MAX_STEP:
            self._waf_step += 1


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _passes_filter(release_type: str, wl_filter: str) -> bool:
    """
    Geeft True als een release door het watchlist filter komt.

    Filters:
      'all'    → altijd door
      'stable' → alleen stable
      'sb'     → stable + beta
      'beta'   → alleen beta
      'alpha'  → alleen alpha
    """
    if wl_filter == "all":
        return True
    if wl_filter == "stable":
        return release_type == "stable"
    if wl_filter in ("sb", "stable+beta"):
        return release_type in ("stable", "beta")
    if wl_filter == "beta":
        return release_type == "beta"
    if wl_filter == "alpha":
        return release_type == "alpha"
    return True  # onbekend filter → alles door


class _DictProject:
    """Minimaal project-object van een dict (uit addon_meta cache)."""
    def __init__(self, d: dict):
        self.id          = d["addon_id"]
        self.name        = d.get("name", "")
        self.slug        = d.get("slug", "")
        self.url         = d.get("url", "")
        self.logo_url    = d.get("logo_url")
        self.downloads   = d.get("downloads", 0)
        self.summary     = d.get("summary", "")
        self.author_name = d.get("author_name", "")


# ─────────────────────────────────────────────────────────────────────────────
# COG SETUP
# ─────────────────────────────────────────────────────────────────────────────

async def setup(bot: commands.Bot):
    await bot.add_cog(CurseForgeCog(bot))

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : curseforge.py (cog)                                 ║
# ║  Role         : Core Monitor                                        ║
# ║  Version      : 3.0.0                                               ║
# ║  Created      : 2026-06-05                                          ║
# ║  Last Updated : 2026-06-05                                          ║
# ║  Status       : New                                                 ║
# ║  Notes        : Volledige monitor loop met history logging          ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
