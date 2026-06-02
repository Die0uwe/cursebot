# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — services/stats.py  v1.0.0
Centrale stats collector — verzamelt runtime data voor het dashboard.
"""
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

START_TIME = time.time()


@dataclass
class BotStats:
    # Runtime
    start_time:         float        = field(default_factory=time.time)
    guilds:             int          = 0
    projects_tracked:   int          = 0
    releases_detected:  int          = 0
    last_check:         Optional[str] = None
    next_check:         Optional[str] = None
    check_interval_min: int          = 10
    # Update info
    last_update_sha:    str          = ""
    last_update_time:   str          = ""
    update_available:   bool         = False
    # CF stats
    cf_author:          str          = ""
    cf_requests_today:  int          = 0
    # Log buffer (laatste 50 regels)
    log_buffer:         list         = field(default_factory=list)

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
            "cf_requests_today": self.cf_requests_today,
            "log_lines":         self.log_buffer[-50:],
        }

    def add_log(self, line: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.log_buffer.append(f"[{ts}] {line}")
        if len(self.log_buffer) > 200:
            self.log_buffer = self.log_buffer[-200:]


# Singleton — gedeeld tussen bot en dashboard
STATS = BotStats()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: stats.py │ Role: Util │ v1.0.0 │ New │ 2026-06-02  15:30   ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
