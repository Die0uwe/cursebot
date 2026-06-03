# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""CurseBot — services/stats.py v2.1.0 — Centrale stats collector.

CHANGES v2.1.0:
  - stop_requested flag toegevoegd (voor dashboard Stop knop)
"""
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class BotStats:
    start_time:          float         = field(default_factory=time.time)
    guilds:              int           = 0
    projects_tracked:    int           = 0
    releases_detected:   int           = 0
    last_check:          Optional[str] = None
    next_check:          Optional[str] = None
    check_interval_min:  int           = 10
    last_update_sha:     str           = ""
    last_update_time:    str           = ""
    update_available:    bool          = False
    cf_author:           str           = ""
    cf_author_id:        Optional[int] = None
    log_buffer:          list          = field(default_factory=list)
    project_list:        list          = field(default_factory=list)
    force_check:         bool          = False
    bot_online:          bool          = False
    stop_requested:      bool          = False   # stop via dashboard
    watchlist_count:     int           = 0       # aantal watchlist items (alle guilds)

    def uptime_str(self) -> str:
        secs = int(time.time() - self.start_time)
        h, rem = divmod(secs, 3600)
        m, s   = divmod(rem, 60)
        return f"{h}u {m}m {s}s"

    def to_dict(self) -> dict:
        return {
            "uptime":            self.uptime_str(),
            "guilds":            self.guilds,
            "projects_tracked":  self.projects_tracked,
            "releases_detected": self.releases_detected,
            "last_check":        self.last_check or "–",
            "next_check":        self.next_check or "–",
            "check_interval":    self.check_interval_min,
            "last_update_sha":   self.last_update_sha or "onbekend",
            "last_update_time":  self.last_update_time or "–",
            "update_available":  self.update_available,
            "cf_author":         self.cf_author,
            "cf_author_id":      self.cf_author_id,
            "log_lines":         self.log_buffer[-50:],
            "bot_online":        self.bot_online,
            "stop_requested":    self.stop_requested,
            "watchlist_count":   self.watchlist_count,
        }

    def add_log(self, line: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.log_buffer.append(f"[{ts}] {line}")
        if len(self.log_buffer) > 500:
            self.log_buffer = self.log_buffer[-500:]


STATS = BotStats()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: stats.py │ v2.2.0 │ 2026-06-03                             ║
# ║  Add: watchlist_count veld voor dashboard stat card               ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
