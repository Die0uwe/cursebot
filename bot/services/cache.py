"""
CurseBot — services/cache.py
SQLite-gebaseerde persistente cache voor CurseForge file IDs.
Geen externe dependencies vereist — werkt out-of-the-box.
"""
import sqlite3
import os
from bot.utils.logger import get_logger

log = get_logger(__name__)


class CacheService:
    """
    Simpele key/value cache op SQLite.
    Thread-safe voor gebruik vanuit asyncio-taken via check-and-set patronen.
    """

    def __init__(self, db_path: str = "cache.db"):
        self._path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kv_cache (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()
        log.debug(f"[CACHE] SQLite cache geïnitialiseerd: {self._path}")

    def get(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM kv_cache WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def set(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO kv_cache (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value)
            )
            conn.commit()

    def delete(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM kv_cache WHERE key = ?", (key,))
            conn.commit()

    def all_keys(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key FROM kv_cache").fetchall()
            return [r["key"] for r in rows]

    def wipe(self) -> None:
        """Verwijder alle cache entries — gebruik alleen bij /reset commando."""
        with self._connect() as conn:
            conn.execute("DELETE FROM kv_cache")
            conn.commit()
        log.warning("[CACHE] Volledige cache gewist.")
