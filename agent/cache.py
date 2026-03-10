import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path


def _get_db_path(config: dict) -> str:
    return config.get("cache", {}).get("db_path", "data/cache.db")


def init_db(config: dict) -> sqlite3.Connection:
    db_path = _get_db_path(config)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_items (
            url_hash TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT,
            source TEXT,
            seen_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode()).hexdigest()


def filter_new_items(conn: sqlite3.Connection, items: list[dict]) -> list[dict]:
    new_items = []
    for item in items:
        h = url_hash(item["url"])
        row = conn.execute(
            "SELECT 1 FROM seen_items WHERE url_hash = ?", (h,)
        ).fetchone()
        if not row:
            new_items.append(item)
    return new_items


def mark_seen(conn: sqlite3.Connection, items: list[dict]) -> None:
    now = datetime.utcnow().isoformat()
    for item in items:
        h = url_hash(item["url"])
        conn.execute(
            "INSERT OR IGNORE INTO seen_items (url_hash, url, title, source, seen_at) VALUES (?, ?, ?, ?, ?)",
            (h, item["url"], item.get("title", ""), item.get("source", ""), now),
        )
    conn.commit()


def cleanup_old_entries(conn: sqlite3.Connection, max_age_days: int = 7) -> None:
    cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()
    conn.execute("DELETE FROM seen_items WHERE seen_at < ?", (cutoff,))
    conn.commit()
