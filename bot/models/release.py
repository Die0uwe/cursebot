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
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum


class ReleaseType(IntEnum):
    RELEASE = 1
    BETA    = 2
    ALPHA   = 3

    def label(self) -> str:
        return {1: "🟢 Release", 2: "🟡 Beta", 3: "🔴 Alpha"}.get(self.value, "⚪ Unknown")

    def color(self) -> int:
        """Discord embed kleur als integer."""
        return {1: 0x00FF88, 2: 0xFFAA00, 3: 0xFF3333}.get(self.value, 0xAAAAAA)


@dataclass
class AddonProject:
    id:          int
    name:        str
    slug:        str
    summary:     str
    url:         str
    logo_url:    str | None = None
    downloads:   int = 0


@dataclass
class AddonRelease:
    file_id:      int
    file_name:    str
    display_name: str
    release_type: ReleaseType
    download_url: str | None
    changelog:    str
    game_versions: list[str] = field(default_factory=list)
    uploaded_at:  datetime | None = None

    def short_changelog(self, max_chars: int = 400) -> str:
        """Kap de changelog af voor gebruik in Discord embeds."""
        text = self.changelog.strip()
        if len(text) > max_chars:
            text = text[:max_chars].rsplit(" ", 1)[0] + "…"
        return text or "_No changelog provided._"

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : release.py                                          ║
# ║  Role         : Core                                                ║
# ║  Version      : 1.0.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-02  13:45                                     ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Datamodellen: AddonProject, AddonRelease, ReleaseType║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
