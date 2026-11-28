from __future__ import annotations

from datetime import timedelta

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .data import complete_daily_from_hourly, resample_to_4h
from .models import Timeframe
from .setups import DAILY_PRESETS, FOUR_HOUR_PRESETS, detect_best_setup
from .store import MarketDataStore, YahooBatchDownloader
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
    min_rs: float = Query(60, ge=0, le=100),  # noqa: B008
    search: str | None = Query(None),
    stages: str | None = Query(  # noqa: B008
        None,
        description="Comma-separated setup stages to keep, e.g. 'Breakout,Ready'.",
    ),
    min_setup_score: int = Query(0, ge=0, le=100),  # noqa: B008
    liquid_only: bool = Query(False),  # noqa: B008
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
        and float(row.get("Setup Score", 0) or 0) >= min_setup_score
    ]

    if stages:
        wanted = {stage.strip() for stage in stages.split(",") if stage.strip()}
        rows = [row for row in rows if row.get("Stage") in wanted]

    if liquid_only:
        rows = [row for row in rows if row.get("Liquid") is True]

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


CHART_CACHE_AGE = timedelta(hours=6)
CHART_LINES = {"EMA10": ("ema", 10), "EMA20": ("ema", 20), "SMA50": ("sma", 50)}
CHART_LINES |= {"SMA150": ("sma", 150), "SMA200": ("sma", 200)}


def _chart_time(value: pd.Timestamp, intraday: bool) -> str | int:
    # Daily bars use business-day strings; intraday bars use UTC epoch seconds.
    return int(value.timestamp()) if intraday else value.strftime("%Y-%m-%d")


@app.get("/api/chart/{symbol}")
def chart(
    symbol: str,
    timeframe: Timeframe = Query(Timeframe.DAILY),  # noqa: B008
    bars: int = Query(260, ge=60, le=1500),  # noqa: B008
) -> dict:
    """OHLCV, moving averages and the detected setup geometry for one symbol."""
    symbol = symbol.upper().strip()
    intraday = timeframe is Timeframe.FOUR_HOUR

    store = MarketDataStore(settings.data_dir, YahooBatchDownloader(pause=0))
    for interval in ("1d", "1h"):
        store.refresh([symbol], interval, max_age=CHART_CACHE_AGE)
    hourly = store.load(symbol, "1h")
    df = (
        resample_to_4h(hourly)
        if intraday
        else complete_daily_from_hourly(store.load(symbol, "1d"), hourly)
    )
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data for {symbol}")

    setup = detect_best_setup(
        df, DAILY_PRESETS if timeframe is Timeframe.DAILY else FOUR_HOUR_PRESETS
    )
    base = setup.base

    start = max(0, len(df) - bars)
    if base is not None:
        start = min(start, max(0, df.index.get_loc(base.start_date) - 20))
    view = df.iloc[start:]

    def when(value: pd.Timestamp) -> str | int:
        return _chart_time(value, intraday)

    close = df["Close"]
    lines = {}
    for name, (kind, period) in CHART_LINES.items():
        series = (
            close.ewm(span=period, adjust=False).mean()
            if kind == "ema"
            else close.rolling(period).mean()
        ).iloc[start:]
        lines[name] = [
            {"time": when(ts), "value": round(float(value), 2)}
            for ts, value in series.items()
            if pd.notna(value)
        ]

    return {
        "symbol": symbol,
        "timeframe": timeframe.value,
        "candles": [
            {
                "time": when(ts),
                "open": round(float(row.Open), 2),
                "high": round(float(row.High), 2),
                "low": round(float(row.Low), 2),
                "close": round(float(row.Close), 2),
                "volume": float(row.Volume),
            }
            for ts, row in zip(view.index, view.itertuples(index=False), strict=True)
        ],
        "lines": lines,
        "setup": {
            "stage": setup.stage.value,
            "setupType": setup.setup_type,
            "score": setup.score,
            "breakoutTime": when(setup.breakout_date) if setup.breakout_date else None,
            "notes": list(setup.notes),
            "base": None
            if base is None
            else {
                "start": when(base.start_date),
                "high": round(base.high, 2),
                "low": round(base.low, 2),
                "pivot": round(base.pivot, 2),
                "stop": round(base.stop, 2),
                "contractions": [
                    {
                        "highTime": when(c.high_date),
                        "high": round(c.high, 2),
                        "lowTime": when(c.low_date),
                        "low": round(c.low, 2),
                        "depthPct": round(c.depth_pct, 1),
                        "shakeout": c.shakeout,
                    }
                    for c in base.contractions
                ],
            },
        },
    }


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
