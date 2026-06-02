# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — config.py  v1.2.0
Fix: model_config gebruikt in plaats van inner Config class (pydantic v2 stijl).
cf_author_id correct als Optional[int] gedefinieerd.
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # ← negeer onbekende env vars
        case_sensitive=False,    # ← CF_AUTHOR_ID en cf_author_id beide werken
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

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: config.py │ v1.2.0 │ Updated │ 2026-06-02  16:30           ║
# ║  Fix: model_config + extra=ignore (pydantic v2) + case_sensitive   ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
