# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""CurseBot — config.py  v1.3.0"""
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
    discord_token:           str
    release_channel_id:      int
    guild_id:                int | None = None

    # CurseForge
    curseforge_api_key:      str
    cf_author_slug:          str        = "dieouwe"
    cf_author_id:            int | None = None
    cf_game_id:              int        = 1

    # Polling
    check_interval_minutes:  int        = 10

    # Database — accepteert zowel DATABASE_PATH als database_path
    database_path:           str        = "cache.db"

    # Logging
    log_level:               str        = "INFO"

    # Dashboard
    dashboard_port:          int        = 5000
    dashboard_enabled:       bool       = True

    # Claude AI
    anthropic_api_key:       str | None = None
    summarize_changelogs:    bool       = False

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
                f"Moet 'dieouwe' zijn, niet het ID getal."
            )
        return v.strip()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: config.py │ v1.3.0 │ 2026-06-02                            ║
# ║  Fix: database_path veld + extra=ignore voorkomt pydantic errors   ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
