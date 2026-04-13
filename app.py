#!/usr/bin/env python3
"""
FastAPI application for the Traktor Finder UI and API.
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from storage import SQLiteDatabase


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = DATA_DIR / "mbtrac.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

db = SQLiteDatabase(DB_PATH)
app = FastAPI(title="Traktor Finder API", version="1.0.0")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/stats")
def stats() -> dict:
    return db.get_stats()


@app.get("/api/listings")
def listings(
    limit: int = Query(default=300, ge=1, le=5000),
    country: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    sort: str = Query(default="newest", pattern="^(newest|price_asc|price_desc)$"),
) -> dict:
    items = db.query_listings(
        limit=limit,
        country=country,
        brand=brand,
        category=category,
        search=search,
        active_only=active_only,
        sort=sort,
    )
    return {"items": items, "count": len(items)}


@app.get("/api/platform-runs/latest")
def latest_platform_runs(limit: int = Query(default=200, ge=1, le=1000)) -> dict:
    items = db.get_latest_platform_runs(limit=limit)
    return {"items": items, "count": len(items)}


@app.get("/api/platform-runs")
def platform_runs(
    scan_run_id: int = Query(..., ge=1),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict:
    items = db.get_platform_runs(scan_run_id=scan_run_id, limit=limit)
    return {"items": items, "count": len(items), "scan_run_id": scan_run_id}


@app.get("/api/scan-runs")
def scan_runs(limit: int = Query(default=20, ge=1, le=200)) -> dict:
    items = db.get_scan_runs(limit=limit)
    return {"items": items, "count": len(items)}
