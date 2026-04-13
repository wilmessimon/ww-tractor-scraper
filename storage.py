#!/usr/bin/env python3
"""
SQLite storage layer for listings, scan runs, and platform status.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class SQLiteDatabase:
    """SQLite-backed source of truth for scraper data."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_json_path = self.db_path.with_suffix(".json")
        self.conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._configure()
        self._init_schema()
        self._migrate_legacy_json_if_needed()

    def _configure(self) -> None:
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                country TEXT NOT NULL,
                title TEXT NOT NULL,
                price TEXT,
                location TEXT,
                url TEXT NOT NULL UNIQUE,
                image_url TEXT,
                description TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                category TEXT NOT NULL DEFAULT 'sonstiges',
                price_numeric REAL,
                is_negotiable INTEGER NOT NULL DEFAULT 0,
                brand TEXT NOT NULL DEFAULT 'mb_trac',
                content_hash TEXT NOT NULL,
                alt_urls_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_listings_active_first_seen
                ON listings(is_active, first_seen DESC);
            CREATE INDEX IF NOT EXISTS idx_listings_country
                ON listings(country);
            CREATE INDEX IF NOT EXISTS idx_listings_brand
                ON listings(brand);
            CREATE INDEX IF NOT EXISTS idx_listings_category
                ON listings(category);
            CREATE INDEX IF NOT EXISTS idx_listings_content_hash
                ON listings(content_hash);

            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                platforms_total INTEGER NOT NULL DEFAULT 0,
                platforms_scanned INTEGER NOT NULL DEFAULT 0,
                platforms_success INTEGER NOT NULL DEFAULT 0,
                platforms_empty INTEGER NOT NULL DEFAULT 0,
                platforms_error INTEGER NOT NULL DEFAULT 0,
                new_listings INTEGER NOT NULL DEFAULT 0,
                total_listings INTEGER NOT NULL DEFAULT 0,
                duration_seconds REAL
            );

            CREATE TABLE IF NOT EXISTS platform_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_run_id INTEGER NOT NULL,
                country_code TEXT NOT NULL,
                platform_name TEXT NOT NULL,
                search_url TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                listings_found INTEGER NOT NULL DEFAULT 0,
                new_listings INTEGER NOT NULL DEFAULT 0,
                duration_seconds REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(scan_run_id) REFERENCES scan_runs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_platform_runs_scan_run
                ON platform_runs(scan_run_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_platform_runs_status
                ON platform_runs(status);
            """
        )
        self.conn.commit()

    @staticmethod
    def _normalize_title(title: str) -> str:
        import re

        normalized = (title or "").lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^\w\s]", "", normalized)
        return normalized

    @classmethod
    def _generate_content_hash(cls, title: str, price_numeric: Optional[float] = None) -> str:
        normalized = cls._normalize_title(title)
        rounded_price = round(price_numeric / 100) * 100 if price_numeric else 0
        raw = f"{normalized}|{rounded_price}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _row_to_listing(row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        try:
            item["alt_urls"] = json.loads(item.pop("alt_urls_json", "[]"))
        except json.JSONDecodeError:
            item["alt_urls"] = []
        item["is_active"] = bool(item.get("is_active", 1))
        item["is_negotiable"] = bool(item.get("is_negotiable", 0))
        return item

    @staticmethod
    def _extract_listing_field(listing: Any, field: str, default: Any = None) -> Any:
        if isinstance(listing, dict):
            return listing.get(field, default)
        return getattr(listing, field, default)

    def _migrate_legacy_json_if_needed(self) -> None:
        count = self.conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        if count > 0 or not self.legacy_json_path.exists():
            return

        try:
            with open(self.legacy_json_path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return

        items = raw.values() if isinstance(raw, dict) else raw
        with self.conn:
            for item in items:
                title = item.get("title", "")
                price_numeric = item.get("price_numeric")
                content_hash = self._generate_content_hash(title, price_numeric)
                alt_urls = item.get("alt_urls", [])
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO listings (
                        id, platform, country, title, price, location, url,
                        image_url, description, first_seen, last_seen, is_active,
                        category, price_numeric, is_negotiable, brand, content_hash,
                        alt_urls_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.get("id"),
                        item.get("platform", "unknown"),
                        item.get("country", "XX"),
                        title,
                        item.get("price"),
                        item.get("location"),
                        item.get("url"),
                        item.get("image_url"),
                        item.get("description"),
                        item.get("first_seen") or datetime.now().isoformat(),
                        item.get("last_seen") or datetime.now().isoformat(),
                        1 if item.get("is_active", True) else 0,
                        item.get("category", "sonstiges"),
                        price_numeric,
                        1 if item.get("is_negotiable") else 0,
                        item.get("brand", "mb_trac"),
                        content_hash,
                        json.dumps(alt_urls, ensure_ascii=False),
                        datetime.now().isoformat(),
                    ),
                )

    def flush(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def listing_exists(self, listing_id: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM listings WHERE id = ?", (listing_id,)).fetchone()
        return row is not None

    def _append_alt_url(self, listing_row: sqlite3.Row, alt_url: str) -> None:
        if not alt_url:
            return
        try:
            urls = json.loads(listing_row["alt_urls_json"] or "[]")
        except json.JSONDecodeError:
            urls = []
        if alt_url in urls or alt_url == listing_row["url"]:
            return
        urls.append(alt_url)
        self.conn.execute(
            "UPDATE listings SET alt_urls_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(urls, ensure_ascii=False), datetime.now().isoformat(), listing_row["id"]),
        )

    def add_listing(self, listing: Any) -> bool:
        listing_id = self._extract_listing_field(listing, "id")
        title = self._extract_listing_field(listing, "title", "")
        price_numeric = self._extract_listing_field(listing, "price_numeric")
        content_hash = self._generate_content_hash(title, price_numeric)
        now = datetime.now().isoformat()

        with self.conn:
            existing = self.conn.execute(
                "SELECT * FROM listings WHERE id = ? OR url = ? LIMIT 1",
                (listing_id, self._extract_listing_field(listing, "url")),
            ).fetchone()

            if existing:
                self.conn.execute(
                    """
                    UPDATE listings
                    SET platform = ?,
                        country = ?,
                        title = ?,
                        price = COALESCE(?, price),
                        location = COALESCE(?, location),
                        image_url = COALESCE(image_url, ?),
                        description = COALESCE(?, description),
                        last_seen = ?,
                        is_active = 1,
                        category = COALESCE(?, category),
                        price_numeric = COALESCE(?, price_numeric),
                        is_negotiable = ?,
                        brand = COALESCE(?, brand),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        self._extract_listing_field(listing, "platform", existing["platform"]),
                        self._extract_listing_field(listing, "country", existing["country"]),
                        title or existing["title"],
                        self._extract_listing_field(listing, "price"),
                        self._extract_listing_field(listing, "location"),
                        self._extract_listing_field(listing, "image_url"),
                        self._extract_listing_field(listing, "description"),
                        self._extract_listing_field(listing, "last_seen", now),
                        self._extract_listing_field(listing, "category"),
                        price_numeric,
                        1 if self._extract_listing_field(listing, "is_negotiable", False) else 0,
                        self._extract_listing_field(listing, "brand"),
                        now,
                        existing["id"],
                    ),
                )
                return False

            duplicate = self.conn.execute(
                "SELECT * FROM listings WHERE content_hash = ? ORDER BY first_seen ASC LIMIT 1",
                (content_hash,),
            ).fetchone()

            if duplicate:
                self.conn.execute(
                    """
                    UPDATE listings
                    SET last_seen = ?,
                        is_active = 1,
                        image_url = COALESCE(image_url, ?),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        self._extract_listing_field(listing, "last_seen", now),
                        self._extract_listing_field(listing, "image_url"),
                        now,
                        duplicate["id"],
                    ),
                )
                self._append_alt_url(duplicate, self._extract_listing_field(listing, "url"))
                return False

            self.conn.execute(
                """
                INSERT INTO listings (
                    id, platform, country, title, price, location, url,
                    image_url, description, first_seen, last_seen, is_active,
                    category, price_numeric, is_negotiable, brand, content_hash,
                    alt_urls_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing_id,
                    self._extract_listing_field(listing, "platform", "unknown"),
                    self._extract_listing_field(listing, "country", "XX"),
                    title,
                    self._extract_listing_field(listing, "price"),
                    self._extract_listing_field(listing, "location"),
                    self._extract_listing_field(listing, "url"),
                    self._extract_listing_field(listing, "image_url"),
                    self._extract_listing_field(listing, "description"),
                    self._extract_listing_field(listing, "first_seen", now),
                    self._extract_listing_field(listing, "last_seen", now),
                    1,
                    self._extract_listing_field(listing, "category", "sonstiges"),
                    price_numeric,
                    1 if self._extract_listing_field(listing, "is_negotiable", False) else 0,
                    self._extract_listing_field(listing, "brand", "mb_trac"),
                    content_hash,
                    json.dumps([], ensure_ascii=False),
                    now,
                ),
            )
            return True

    def get_new_listings(self, since: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM listings
            WHERE first_seen >= ?
            ORDER BY first_seen DESC
            """,
            (since,),
        ).fetchall()
        return [self._row_to_listing(row) for row in rows]

    def get_all_active(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = """
            SELECT * FROM listings
            WHERE is_active = 1
            ORDER BY first_seen DESC
        """
        params: List[Any] = []
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_listing(row) for row in rows]

    def query_listings(
        self,
        *,
        limit: int = 300,
        country: Optional[str] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        active_only: bool = True,
        sort: str = "newest",
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []

        if active_only:
            clauses.append("is_active = 1")
        if country:
            clauses.append("country = ?")
            params.append(country)
        if brand:
            clauses.append("brand = ?")
            params.append(brand)
        if category:
            clauses.append("category = ?")
            params.append(category)
        if search:
            clauses.append("LOWER(title) LIKE ?")
            params.append(f"%{search.lower()}%")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        order_by = "first_seen DESC"
        if sort == "price_asc":
            order_by = "COALESCE(price_numeric, 0) ASC, first_seen DESC"
        elif sort == "price_desc":
            order_by = "COALESCE(price_numeric, 0) DESC, first_seen DESC"

        rows = self.conn.execute(
            f"""
            SELECT * FROM listings
            {where}
            ORDER BY {order_by}
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [self._row_to_listing(row) for row in rows]

    def get_stats(self) -> Dict[str, Any]:
        today = datetime.now().strftime("%Y-%m-%d")

        totals = self.conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active
            FROM listings
            """
        ).fetchone()

        by_country_rows = self.conn.execute(
            """
            SELECT country, COUNT(*) AS count
            FROM listings
            WHERE is_active = 1
            GROUP BY country
            ORDER BY count DESC, country ASC
            """
        ).fetchall()

        by_brand_rows = self.conn.execute(
            """
            SELECT brand, COUNT(*) AS count
            FROM listings
            WHERE is_active = 1
            GROUP BY brand
            ORDER BY count DESC, brand ASC
            """
        ).fetchall()

        new_today = self.conn.execute(
            "SELECT COUNT(*) FROM listings WHERE first_seen LIKE ?",
            (f"{today}%",),
        ).fetchone()[0]

        latest_scan = self.conn.execute(
            "SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

        return {
            "total": totals["total"] or 0,
            "active": totals["active"] or 0,
            "new_today": new_today or 0,
            "by_country": {row["country"]: row["count"] for row in by_country_rows},
            "by_brand": {row["brand"]: row["count"] for row in by_brand_rows},
            "latest_scan": dict(latest_scan) if latest_scan else None,
        }

    def start_scan_run(self, platforms_total: int) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO scan_runs (started_at, status, platforms_total)
            VALUES (?, 'running', ?)
            """,
            (datetime.now().isoformat(), platforms_total),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def finish_scan_run(
        self,
        scan_run_id: int,
        *,
        platforms_scanned: int,
        new_listings: int,
        total_listings: int,
        duration_seconds: float,
        platforms_success: int,
        platforms_empty: int,
        platforms_error: int,
    ) -> None:
        status = "completed" if platforms_error == 0 else "completed_with_errors"
        self.conn.execute(
            """
            UPDATE scan_runs
            SET finished_at = ?,
                status = ?,
                platforms_scanned = ?,
                platforms_success = ?,
                platforms_empty = ?,
                platforms_error = ?,
                new_listings = ?,
                total_listings = ?,
                duration_seconds = ?
            WHERE id = ?
            """,
            (
                datetime.now().isoformat(),
                status,
                platforms_scanned,
                platforms_success,
                platforms_empty,
                platforms_error,
                new_listings,
                total_listings,
                duration_seconds,
                scan_run_id,
            ),
        )
        self.conn.commit()

    def log_scan(self, platforms: int, new_listings: int, total: int, duration: float) -> None:
        scan_run_id = self.start_scan_run(platforms)
        self.finish_scan_run(
            scan_run_id,
            platforms_scanned=platforms,
            new_listings=new_listings,
            total_listings=total,
            duration_seconds=duration,
            platforms_success=platforms,
            platforms_empty=0,
            platforms_error=0,
        )

    def log_platform_run(
        self,
        *,
        scan_run_id: int,
        country_code: str,
        platform_name: str,
        search_url: str,
        status: str,
        error_message: Optional[str],
        listings_found: int,
        new_listings: int,
        duration_seconds: float,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO platform_runs (
                scan_run_id, country_code, platform_name, search_url, status,
                error_message, listings_found, new_listings, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_run_id,
                country_code,
                platform_name,
                search_url,
                status,
                error_message,
                listings_found,
                new_listings,
                duration_seconds,
            ),
        )
        self.conn.commit()

    def get_latest_platform_runs(self, limit: int = 200) -> List[Dict[str, Any]]:
        latest = self.conn.execute("SELECT MAX(id) AS id FROM scan_runs").fetchone()
        if not latest or latest["id"] is None:
            return []
        return self.get_platform_runs(scan_run_id=int(latest["id"]), limit=limit)

    def get_platform_runs(self, scan_run_id: int, limit: int = 200) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM platform_runs
            WHERE scan_run_id = ?
            ORDER BY
                CASE status
                    WHEN 'error' THEN 0
                    WHEN 'empty' THEN 1
                    ELSE 2
                END,
                platform_name ASC
            LIMIT ?
            """,
            (scan_run_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_scan_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM scan_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
