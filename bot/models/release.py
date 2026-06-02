"""
CurseBot — models/release.py
Datamodellen voor CurseForge projecten en releases.
"""
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
