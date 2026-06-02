# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — config.py  v1.1.0
Alle settings via environment variables / .env bestand.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # Discord
    discord_token:      str
    release_channel_id: int
    guild_id:           int | None = None

    # CurseForge
    curseforge_api_key: str
    cf_author_slug:     str       = "dieouwe"
    cf_author_id:       int | None = None   # Numerieke ID — gebruik find_author_id.py
    cf_game_id:         int       = 1

    # Polling
    check_interval_minutes: int   = 10

    # Database
    database_path:      str       = "cache.db"

    # Logging
    log_level:          str       = "INFO"

    # Dashboard
    dashboard_port:     int       = 5000
    dashboard_enabled:  bool      = True

    # Claude API
    anthropic_api_key:  str | None = None
    summarize_changelogs: bool     = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level moet een van {allowed} zijn")
        return v

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: config.py │ v1.1.0 │ Updated │ 2026-06-02  15:45           ║
# ║  Notes: CF_AUTHOR_ID + DASHBOARD_PORT/ENABLED toegevoegd           ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
