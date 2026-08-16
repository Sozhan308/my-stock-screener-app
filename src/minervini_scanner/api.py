from __future__ import annotations

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .models import Timeframe
from .watchlist import WatchlistStore

settings = get_settings()

watchlist_store = WatchlistStore(settings.watchlist_db)

app = FastAPI(
    title="Minervini NSE Scanner API",
    version="0.2.0",
    description="REST API for the Minervini NSE stock scanner.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load(timeframe: Timeframe) -> list[dict]:
    path = settings.output_dir / f"minervini_{timeframe.value}.csv"

    if not path.exists():
        return []

    df = pd.read_csv(path)

    # Convert NumPy/Pandas values into JSON-safe Python values.
    records = df.where(pd.notna(df), None).to_dict(orient="records")

    for record in records:
        for key, value in list(record.items()):
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                continue
            if hasattr(value, "item"):
                record[key] = value.item()

    return records


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/stocks")
def stocks(
    timeframe: Timeframe = Query(Timeframe.DAILY),  # noqa: B008
    min_score: int = Query(7, ge=0, le=9),  # noqa: B008
    min_rs: float = Query(70, ge=0, le=100),  # noqa: B008
    search: str | None = Query(None),
) -> dict:
    rows = _load(timeframe)

    if search:
        search_upper = search.upper().strip()
        rows = [row for row in rows if search_upper in str(row.get("Symbol", "")).upper()]

    rows = [
        row
        for row in rows
        if float(row.get("Score", 0) or 0) >= min_score
        and float(row.get("RS Rating", 0) or 0) >= min_rs
    ]

    return {
        "timeframe": timeframe.value,
        "count": len(rows),
        "stocks": rows,
    }


@app.get("/api/stocks/{symbol}")
def stock(
    symbol: str,
    timeframe: Timeframe = Query(Timeframe.DAILY),  # noqa: B008
) -> dict:
    rows = _load(timeframe)
    symbol = symbol.upper()

    for row in rows:
        if row.get("Symbol") == symbol:
            return row

    raise HTTPException(status_code=404, detail=f"{symbol} not found")


@app.get("/api/watchlist")
def get_watchlist() -> dict:
    return {
        "symbols": watchlist_store.list_symbols(),
    }


@app.post("/api/watchlist/{symbol}")
def add_to_watchlist(symbol: str) -> dict:
    symbol = symbol.upper().strip()

    if not symbol:
        raise HTTPException(
            status_code=400,
            detail="Symbol is required",
        )

    watchlist_store.add(symbol)

    return {
        "symbol": symbol,
        "saved": True,
    }


@app.delete("/api/watchlist/{symbol}")
def remove_from_watchlist(symbol: str) -> dict:
    symbol = symbol.upper().strip()

    watchlist_store.remove(symbol)

    return {
        "symbol": symbol,
        "saved": False,
    }
