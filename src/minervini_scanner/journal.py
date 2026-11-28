"""Replay the setup detector as of past trade dates, e.g. entries from a trading journal."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .data import complete_daily_from_hourly, resample_to_4h
from .setups import (
    ACTIONABLE_STAGES,
    DAILY_PRESETS,
    FOUR_HOUR_PRESETS,
    SetupResult,
    detect_best_setup,
)
from .store import MarketDataStore


@dataclass(frozen=True)
class TradeCheck:
    symbol: str
    date: pd.Timestamp
    daily_before: SetupResult
    daily_on: SetupResult
    four_hour_before: SetupResult
    four_hour_on: SetupResult

    @property
    def detected(self) -> bool:
        return any(
            result.stage in ACTIONABLE_STAGES
            for result in (
                self.daily_before,
                self.daily_on,
                self.four_hour_before,
                self.four_hour_on,
            )
        )


def load_trades(path: Path) -> pd.DataFrame:
    """Read a CSV with ``symbol`` and ``date`` columns (case-insensitive)."""
    df = pd.read_csv(path)
    df.columns = [column.strip().lower() for column in df.columns]
    missing = {"symbol", "date"} - set(df.columns)
    if missing:
        raise ValueError(f"Trades CSV is missing columns: {', '.join(sorted(missing))}")
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    df["date"] = pd.to_datetime(df["date"])
    return df


def _before(df: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return df
    index = df.index.tz_convert("Asia/Kolkata").tz_localize(None) if df.index.tz else df.index
    return df[index < cutoff]


def check_trade(store: MarketDataStore, symbol: str, date: pd.Timestamp) -> TradeCheck:
    """Detector state at the close before the trade date and at the trade-date close."""
    hourly = store.load(symbol, "1h")
    daily = complete_daily_from_hourly(store.load(symbol, "1d"), hourly)
    four_hour = resample_to_4h(hourly)
    day = date.normalize()
    next_day = day + pd.Timedelta(days=1)
    return TradeCheck(
        symbol=symbol,
        date=day,
        daily_before=detect_best_setup(_before(daily, day), DAILY_PRESETS),
        daily_on=detect_best_setup(_before(daily, next_day), DAILY_PRESETS),
        four_hour_before=detect_best_setup(_before(four_hour, day), FOUR_HOUR_PRESETS),
        four_hour_on=detect_best_setup(_before(four_hour, next_day), FOUR_HOUR_PRESETS),
    )


def check_trades(store: MarketDataStore, trades: pd.DataFrame) -> list[TradeCheck]:
    symbols = trades["symbol"].drop_duplicates().tolist()
    store.refresh(symbols, "1d")
    store.refresh(symbols, "1h")
    return [check_trade(store, row.symbol, row.date) for row in trades.itertuples(index=False)]
