# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — config.py  v1.3.0

CHANGES v1.3.0:
  - Settings.load() methode: keyring → .env → os.environ (via key_manager)
  - Backwards compatible: Settings() werkt nog steeds puur via .env
  - __repr__ maskeert tokens en API keys
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Discord
    discord_token:          str
    release_channel_id:     int
    guild_id:               int | None = None

    # CurseForge
    curseforge_api_key:     str
    cf_author_slug:         str        = "dieouwe"
    cf_author_id:           int | None = None
    cf_game_id:             int        = 1

    # Polling
    check_interval_minutes: int        = 10

    # Database
    database_path:          str        = "cache.db"

    # Logging
    log_level:              str        = "INFO"

    # Dashboard
    dashboard_port:         int        = 5000
    dashboard_enabled:      bool       = True

    # Claude AI
    anthropic_api_key:      str | None = None
    summarize_changelogs:   bool       = False

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level moet een van {allowed} zijn")
        return v

    @field_validator("cf_author_slug")
    @classmethod
    def validate_cf_author_slug(cls, v: str) -> str:
        if v.strip().isdigit():
            import logging
            logging.getLogger(__name__).error(
                f"CF_AUTHOR_SLUG='{v}' is een getal! "
                f"Dit hoort een naam te zijn zoals 'dieouwe'."
            )
        return v.strip()

    def __repr__(self) -> str:
        """Maskeert gevoelige waarden in logs en debug output."""
        return (
            f"Settings("
            f"cf_author_slug={self.cf_author_slug!r}, "
            f"cf_author_id={self.cf_author_id}, "
            f"check_interval_minutes={self.check_interval_minutes}, "
            f"discord_token='••••••••', "
            f"curseforge_api_key='••••••••'"
            f")"
        )

    @classmethod
    def load(cls) -> "Settings":
        """
        Laad Settings met keyring als primaire bron.
        Vult ontbrekende waarden aan via .env en os.environ.

        Gebruik dit in main.py ipv Settings() direct.
        """
        try:
            from bot.services.key_manager import get_key
            overrides = {}

            mapping = {
                "discord_token":      "DISCORD_TOKEN",
                "curseforge_api_key": "CURSEFORGE_API_KEY",
                "release_channel_id": "RELEASE_CHANNEL_ID",
                "cf_author_slug":     "CF_AUTHOR_SLUG",
                "cf_author_id":       "CF_AUTHOR_ID",
                "guild_id":           "GUILD_ID",
                "check_interval_minutes": "CHECK_INTERVAL_MINUTES",
                "log_level":          "LOG_LEVEL",
                "anthropic_api_key":  "ANTHROPIC_API_KEY",
            }

            for field, env_key in mapping.items():
                val = get_key(env_key)
                if val:
                    # Converteer numerieke velden
                    if field in ("release_channel_id", "cf_author_id",
                                 "guild_id", "check_interval_minutes"):
                        try:
                            val = int(val)
                        except (ValueError, TypeError):
                            continue
                    overrides[field] = val

            if overrides:
                return cls(**overrides)

        except ImportError:
            pass  # key_manager niet beschikbaar — val terug op .env

        return cls()  # Standaard: puur via .env


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: config.py │ v1.3.0 │ 2026-06-03                            ║
# ║  Add: Settings.load() met keyring integratie                       ║
# ║  Add: __repr__ maskeert tokens                                     ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
