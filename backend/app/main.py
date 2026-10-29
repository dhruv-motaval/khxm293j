from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analytics import dashboard_payload
from .config import settings
from .elexon import ElexonError, fetch_month

app = FastAPI(
    title="Wind Forecast Workbench API",
    version="1.0.0",
    description="Day-ahead UK wind forecast review using Elexon FUELHH and WINDFOR only.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_cache_lock = asyncio.Lock()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "wind-forecast-workbench"}


@app.get("/api/dashboard")
async def get_dashboard(
    month: str = Query(default="2026-01", pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    cutoff: str = Query(default="09:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$"),
) -> dict[str, Any]:
    cache_key = f"{month}:{cutoff}"
    now = time.monotonic()
    async with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < settings.cache_ttl_seconds:
            return cached[1]
    try:
        payload = dashboard_payload(await fetch_month(month, cutoff))
    except ElexonError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid month or cutoff: {exc}") from exc
    except Exception as exc:  # Avoid leaking stack traces or internals to the browser.
        raise HTTPException(status_code=502, detail="Unable to retrieve or process Elexon data. Retry shortly.") from exc
    async with _cache_lock:
        _cache[cache_key] = (time.monotonic(), payload)
    return payload


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "Wind Forecast Workbench API", "docs": "/docs", "health": "/health"}
