# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — services/cache.py  v2.0.0

DB schema v2:
  file_cache    - bijgehouden file IDs (bestaand)
  watchlist     - per guild getrackte addons (NIEUW)
  addon_meta    - gecachte addon metadata (NIEUW)

Migratie: automatisch bij startup via _migrate()
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from bot.utils.logger import get_logger

log = get_logger(__name__)

DB_VERSION = 4


class CacheService:
    def __init__(self, db_path: str = "cache.db"):
        self._path = str(Path(db_path))
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._connect() as conn:
            # Versie tabel
            conn.execute("""
                CREATE TABLE IF NOT EXISTS db_meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            # File cache (bestaand)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    key        TEXT PRIMARY KEY,
                    value      TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            # Watchlist (NIEUW v2)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id    TEXT    NOT NULL,
                    addon_id    INTEGER NOT NULL,
                    addon_name  TEXT    NOT NULL,
                    addon_slug  TEXT    NOT NULL DEFAULT '',
                    addon_url   TEXT    NOT NULL DEFAULT '',
                    author_name TEXT    NOT NULL DEFAULT '',
                    downloads   INTEGER NOT NULL DEFAULT 0,
                    logo_url    TEXT,
                    release_filter TEXT NOT NULL DEFAULT 'all',
                    added_by    TEXT    NOT NULL DEFAULT 'system',
                    added_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(guild_id, addon_id)
                )
            """)
            # Addon metadata cache (NIEUW v2)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS addon_meta (
                    addon_id    INTEGER PRIMARY KEY,
                    name        TEXT    NOT NULL,
                    slug        TEXT    NOT NULL DEFAULT '',
                    author_name TEXT    NOT NULL DEFAULT '',
                    summary     TEXT    NOT NULL DEFAULT '',
                    url         TEXT    NOT NULL DEFAULT '',
                    logo_url    TEXT,
                    downloads   INTEGER NOT NULL DEFAULT 0,
                    cached_at   TEXT    NOT NULL DEFAULT (datetime('now'))
                )
            """)

            # Download statistieken (NIEUW v3)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_stats (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    addon_id   INTEGER NOT NULL,
                    downloads  INTEGER NOT NULL DEFAULT 0,
                    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(addon_id, recorded_at)
                )
            """)
            # Channel config per guild (NIEUW v3)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_config (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id     TEXT    NOT NULL,
                    channel_type TEXT    NOT NULL DEFAULT 'all',
                    channel_id   INTEGER NOT NULL,
                    added_at     TEXT    NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(guild_id, channel_type)
                )
            """)
            # Release history (NIEUW v4) — log van alle verstuurde notificaties
            conn.execute("""
                CREATE TABLE IF NOT EXISTS release_history (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    addon_id     INTEGER NOT NULL,
                    addon_name   TEXT    NOT NULL,
                    file_id      INTEGER NOT NULL,
                    display_name TEXT    NOT NULL DEFAULT \'\',
                    release_type TEXT    NOT NULL DEFAULT \'Stable\',
                    notified_at  TEXT    NOT NULL DEFAULT (datetime(\'now\')),
                    UNIQUE(addon_id, file_id)
                )
            """)
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection):
        row = conn.execute(
            "SELECT value FROM db_meta WHERE key='version'"
        ).fetchone()
        current = int(row["value"]) if row else 1

        if current < 2:
            log.info("[DB] Migratie v1→v2: watchlist + addon_meta")
        if current < 3:
            log.info("[DB] Migratie v2→v3: download_stats + channel_config")
        if current < 3:
            log.info("[DB] Migratie v2→v3: download_stats + channel_config")
        if current < 4:
            log.info("[DB] Migratie v3→v4: release_history")
        if current < 4 or not row:
            conn.execute(
                "INSERT OR REPLACE INTO db_meta VALUES ('version','4')"
            )

    # ── File cache (bestaand) ──────────────────────────────────────────────────
    def get(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM file_cache WHERE key=?", (key,)
            ).fetchone()
            return row["value"] if row else None

    def set(self, key: str, value: str):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO file_cache(key,value,updated_at)
                   VALUES(?,?,datetime('now'))
                   ON CONFLICT(key) DO UPDATE SET
                     value=excluded.value,
                     updated_at=excluded.updated_at""",
                (key, value)
            )

    def delete(self, key: str):
        with self._connect() as conn:
            conn.execute("DELETE FROM file_cache WHERE key=?", (key,))

    def all_keys(self) -> list[str]:
        with self._connect() as conn:
            return [r["key"] for r in conn.execute(
                "SELECT key FROM file_cache"
            ).fetchall()]

    def wipe(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM file_cache")
        log.info("[DB] File cache gewist")

    # ── Watchlist ──────────────────────────────────────────────────────────────
    def watchlist_add(
        self, guild_id: str, addon_id: int, addon_name: str,
        addon_slug: str = "", addon_url: str = "",
        author_name: str = "", downloads: int = 0,
        logo_url: str | None = None,
        release_filter: str = "all", added_by: str = "system"
    ) -> bool:
        """Voeg addon toe aan watchlist. Geeft True als nieuw, False als al bestaat."""
        try:
            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO watchlist
                      (guild_id,addon_id,addon_name,addon_slug,addon_url,
                       author_name,downloads,logo_url,release_filter,added_by)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (guild_id, addon_id, addon_name, addon_slug, addon_url,
                      author_name, downloads, logo_url, release_filter, added_by))
            log.info(f"[DB] Watchlist: {addon_name} toegevoegd voor guild {guild_id}")
            return True
        except sqlite3.IntegrityError:
            return False  # Al in watchlist

    def watchlist_remove(self, guild_id: str, addon_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM watchlist WHERE guild_id=? AND addon_id=?",
                (guild_id, addon_id)
            )
            removed = cur.rowcount > 0
        if removed:
            log.info(f"[DB] Watchlist: addon {addon_id} verwijderd voor guild {guild_id}")
        return removed

    def watchlist_remove_by_name(self, guild_id: str, name: str) -> tuple[bool, str]:
        """Verwijder op naam (case-insensitive). Geeft (success, addon_name)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT addon_id, addon_name FROM watchlist WHERE guild_id=? AND LOWER(addon_name) LIKE ?",
                (guild_id, f"%{name.lower()}%")
            ).fetchone()
            if not row:
                return False, ""
            conn.execute(
                "DELETE FROM watchlist WHERE guild_id=? AND addon_id=?",
                (guild_id, row["addon_id"])
            )
        return True, row["addon_name"]

    def watchlist_get(self, guild_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM watchlist WHERE guild_id=? ORDER BY addon_name",
                (guild_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def watchlist_all(self) -> list[dict]:
        """Alle watchlist items over alle guilds — voor de monitor loop."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM watchlist ORDER BY guild_id, addon_name"
            ).fetchall()
        return [dict(r) for r in rows]

    def watchlist_exists(self, guild_id: str, addon_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM watchlist WHERE guild_id=? AND addon_id=?",
                (guild_id, addon_id)
            ).fetchone()
        return row is not None

    def watchlist_count(self, guild_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM watchlist WHERE guild_id=?",
                (guild_id,)
            ).fetchone()
        return row["c"]

    # ── Addon metadata cache ───────────────────────────────────────────────────
    def addon_meta_set(self, addon_id: int, data: dict):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO addon_meta
                  (addon_id,name,slug,author_name,summary,url,logo_url,downloads,cached_at)
                VALUES (?,?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(addon_id) DO UPDATE SET
                  name=excluded.name, slug=excluded.slug,
                  author_name=excluded.author_name, summary=excluded.summary,
                  url=excluded.url, logo_url=excluded.logo_url,
                  downloads=excluded.downloads, cached_at=excluded.cached_at
            """, (
                addon_id,
                data.get("name",""), data.get("slug",""),
                data.get("author_name",""), data.get("summary",""),
                data.get("url",""), data.get("logo_url"),
                data.get("downloads",0)
            ))

    def addon_meta_get(self, addon_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM addon_meta WHERE addon_id=?", (addon_id,)
            ).fetchone()
        return dict(row) if row else None


    # ── Download statistieken ──────────────────────────────────────────────────
    def stats_record(self, addon_id: int, downloads: int):
        """Sla huidige download count op voor trend analyse."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:00:00")
        with self._connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO download_stats(addon_id,downloads,recorded_at)
                   VALUES(?,?,?)""",
                (addon_id, downloads, ts)
            )

    def stats_get_trend(self, addon_id: int, days: int = 7) -> list[dict]:
        """Haal download trend op voor de laatste N dagen."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT downloads, recorded_at FROM download_stats
                   WHERE addon_id=?
                     AND recorded_at >= datetime('now', ?)
                   ORDER BY recorded_at ASC""",
                (addon_id, f"-{days} days")
            ).fetchall()
        return [dict(r) for r in rows]

    def stats_growth(self, addon_id: int) -> int:
        """Downloads verschil laatste 24u. Positief = groei."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT downloads FROM download_stats
                   WHERE addon_id=?
                   ORDER BY recorded_at DESC LIMIT 2""",
                (addon_id,)
            ).fetchall()
        if len(rows) < 2:
            return 0
        return rows[0]["downloads"] - rows[1]["downloads"]

    def stats_all_totals(self) -> list[dict]:
        """Totaal downloads per addon — meest recente meting."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT addon_id, downloads, recorded_at
                   FROM download_stats
                   WHERE (addon_id, recorded_at) IN (
                     SELECT addon_id, MAX(recorded_at)
                     FROM download_stats GROUP BY addon_id
                   )
                   ORDER BY downloads DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Channel configuratie ───────────────────────────────────────────────────
    def channel_set(self, guild_id: str, channel_type: str, channel_id: int):
        """
        Sla channel ID op voor een bepaald release type.
        channel_type: 'all' | 'stable' | 'beta' | 'alpha'
        """
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO channel_config(guild_id,channel_type,channel_id)
                   VALUES(?,?,?)
                   ON CONFLICT(guild_id,channel_type) DO UPDATE SET
                     channel_id=excluded.channel_id""",
                (guild_id, channel_type, channel_id)
            )
        log.info(f"[DB] Channel config: guild={guild_id} type={channel_type} ch={channel_id}")

    def channel_get(self, guild_id: str, release_type: str = "all") -> int | None:
        """
        Haal channel ID op voor release type.
        Fallback: 'all' channel als specifiek type niet geconfigureerd.
        """
        with self._connect() as conn:
            # Probeer specifiek type
            row = conn.execute(
                "SELECT channel_id FROM channel_config WHERE guild_id=? AND channel_type=?",
                (guild_id, release_type)
            ).fetchone()
            if row:
                return row["channel_id"]
            # Fallback naar 'all'
            row = conn.execute(
                "SELECT channel_id FROM channel_config WHERE guild_id=? AND channel_type='all'",
                (guild_id,)
            ).fetchone()
        return row["channel_id"] if row else None

    def channel_list(self, guild_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM channel_config WHERE guild_id=? ORDER BY channel_type",
                (guild_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def channel_remove(self, guild_id: str, channel_type: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM channel_config WHERE guild_id=? AND channel_type=?",
                (guild_id, channel_type)
            )
        return cur.rowcount > 0

    # ── Release history ───────────────────────────────────────────────────────
    def release_history_add(
        self,
        addon_id:     int,
        addon_name:   str,
        file_id:      int,
        display_name: str = "",
        release_type: str = "Stable",
    ) -> bool:
        """
        Sla een nieuwe release op in de history.
        Geeft True als nieuw opgeslagen, False als file_id al bekend was.
        """
        try:
            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO release_history
                      (addon_id, addon_name, file_id, display_name, release_type)
                    VALUES (?,?,?,?,?)
                """, (addon_id, addon_name, file_id, display_name, release_type))
            log.info(f"[DB] History: {addon_name} {display_name} ({release_type}) opgeslagen")
            return True
        except sqlite3.IntegrityError:
            return False  # Al opgeslagen

    def release_history_get(self, limit: int = 10) -> list[dict]:
        """
        Haal de laatste N releases op — voor /history command.
        Gesorteerd: nieuwste eerst.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT addon_name, display_name, release_type, notified_at
                   FROM release_history
                   ORDER BY notified_at DESC
                   LIMIT ?""",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def release_history_count(self) -> int:
        """Totaal aantal release notificaties ooit verstuurd."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM release_history"
            ).fetchone()
        return row["c"] if row else 0

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: cache.py │ v2.0.0 │ 2026-06-02                             ║
# ║  DB v3: download_stats + channel_config + trend analyse            ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
