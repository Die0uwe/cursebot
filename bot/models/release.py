# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""CurseBot — models/release.py  v2.0.0"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Optional


class ReleaseType(IntEnum):
    RELEASE = 1
    BETA    = 2
    ALPHA   = 3

    @property
    def label(self) -> str:
        return {1: "Stable", 2: "Beta", 3: "Alpha"}[self.value]

    @property
    def emoji(self) -> str:
        return {1: "✅", 2: "🟡", 3: "🔴"}[self.value]

    @property
    def color(self) -> int:
        return {1: 0x2ecc71, 2: 0xf5a623, 3: 0xe74c3c}[self.value]


@dataclass
class AddonProject:
    id:          int
    name:        str
    slug:        str
    summary:     str        = ""
    url:         str        = ""
    logo_url:    str | None = None
    downloads:   int        = 0
    author_name: str        = ""   # NIEUW v2


@dataclass
class AddonRelease:
    file_id:      int
    file_name:    str
    display_name: str
    release_type: ReleaseType
    download_url: str | None        = None
    changelog:    str               = ""
    game_versions: list             = field(default_factory=list)
    uploaded_at:  datetime | None   = None

    def matches_filter(self, release_filter: str) -> bool:
        """Controleer of deze release past binnen het ingestelde filter."""
        if release_filter == "all":
            return True
        if release_filter == "stable":
            return self.release_type == ReleaseType.RELEASE
        if release_filter == "stable_beta":
            return self.release_type in (ReleaseType.RELEASE, ReleaseType.BETA)
        return True

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: release.py │ v2.0.0 │ 2026-06-02 │ author_name + filter    ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
