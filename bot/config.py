"""
CurseBot — config.py
Alle settings via environment variables / .env bestand.
NOOIT hardcode secrets — laad altijd via .env
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # Discord
    discord_token: str
    release_channel_id: int           # Channel waar release embeds naartoe gaan
    guild_id: int | None = None       # Voor dev: slash commands alleen voor deze guild

    # CurseForge
    curseforge_api_key: str
    cf_author_slug: str = "dieouwe"   # Auteur slug op CurseForge
    cf_game_id: int = 1               # 1 = World of Warcraft

    # Polling
    check_interval_minutes: int = 10  # Hoe vaak pollen (10 min is veilig binnen CF rate limits)

    # Database
    database_path: str = "cache.db"   # SQLite pad

    # Logging
    log_level: str = "INFO"

    # Optioneel: Claude API voor changelog samenvatting
    anthropic_api_key: str | None = None
    summarize_changelogs: bool = False

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
