# ==============================================================================
# Copyright (C) 2026  DieOuwe (https://www.dieouwe.nl / https://www.slayeralliance.com)
#
# This work is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This work is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# ==============================================================================
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

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : config.py                                           ║
# ║  Role         : Core                                                ║
# ║  Version      : 1.0.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-02  13:45                                     ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Settings via pydantic-settings / .env               ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
