"""Local OHLCV cache with incremental, batched Yahoo Finance downloads.

Bars are stored as one Parquet file per symbol and interval under ``root/<interval>/``.
Refreshes only download a short overlap window for symbols that are already cached; when the
overlap no longer matches the cached bars (split/dividend re-adjustment) the full history is
re-downloaded for that symbol.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Protocol

import pandas as pd
import yfinance as yf

OHLCV = ["Open", "High", "Low", "Close", "Volume"]


@dataclass(frozen=True)
class IntervalSpec:
    full_period: str
    overlap: timedelta
    max_history: timedelta | None = None
    # Retried for symbols whose full download fails (Yahoo rejects 730d hourly requests for
    # stocks listed within roughly the last two years).
    fallback_period: str | None = None


INTERVALS: dict[str, IntervalSpec] = {
    "1d": IntervalSpec(full_period="5y", overlap=timedelta(days=10)),
    # Yahoo only serves ~730 days of hourly bars.
    "1h": IntervalSpec(
        full_period="730d",
        overlap=timedelta(days=5),
        max_history=timedelta(days=720),
        fallback_period="1y",
    ),
}


class Downloader(Protocol):
    def __call__(
        self,
        symbols: list[str],
        interval: str,
        *,
        period: str | None = None,
        start: str | None = None,
    ) -> dict[str, pd.DataFrame]: ...


def _batches(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def empty_bars() -> pd.DataFrame:
    return pd.DataFrame(columns=OHLCV, index=pd.DatetimeIndex([], name="Date"), dtype=float)


def clean_bars(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return empty_bars()
    result = df[OHLCV].dropna(subset=["Open", "High", "Low", "Close"]).astype(float)
    result = result[~result.index.duplicated(keep="last")].sort_index()
    result.index.name = "Date"
    return result


class YahooBatchDownloader:
    def __init__(self, batch_size: int = 100, pause: float = 0.5, suffix: str = ".NS") -> None:
        self.batch_size = batch_size
        self.pause = pause
        self.suffix = suffix

    def __call__(
        self,
        symbols: list[str],
        interval: str,
        *,
        period: str | None = None,
        start: str | None = None,
    ) -> dict[str, pd.DataFrame]:
        result: dict[str, pd.DataFrame] = {}
        for chunk in _batches(symbols, self.batch_size):
            tickers = [f"{symbol}{self.suffix}" for symbol in chunk]
            raw = yf.download(
                tickers,
                period=period,
                start=start,
                interval=interval,
                auto_adjust=True,
                group_by="ticker",
                progress=False,
                threads=True,
            )
            for symbol, ticker in zip(chunk, tickers, strict=True):
                frame = self._extract(raw, ticker)
                if not frame.empty:
                    result[symbol] = frame
            if self.pause:
                time.sleep(self.pause)
        return result

    @staticmethod
    def _extract(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
        if raw.empty:
            return empty_bars()
        if isinstance(raw.columns, pd.MultiIndex):
            if ticker not in raw.columns.get_level_values(0):
                return empty_bars()
            frame = raw[ticker]
        else:
            frame = raw
        return clean_bars(frame)


def merge_bars(
    cached: pd.DataFrame,
    fresh: pd.DataFrame,
    tolerance: float = 0.005,
) -> pd.DataFrame | None:
    """Append ``fresh`` to ``cached``.

    Returns ``None`` when the histories disagree (price re-adjustment or a gap), signalling
    that a full re-download is required.
    """
    if cached.empty:
        return fresh
    if fresh.empty:
        return cached

    overlap = cached.index.intersection(fresh.index)
    # The last cached bar may have been captured intraday, so it is not compared.
    overlap = overlap[overlap < cached.index[-1]]
    if overlap.empty:
        return None

    drift = (fresh.loc[overlap, "Close"] / cached.loc[overlap, "Close"] - 1).abs()
    if float(drift.max()) > tolerance:
        return None

    combined = pd.concat([cached[cached.index < fresh.index[0]], fresh])
    return combined[~combined.index.duplicated(keep="last")].sort_index()


@dataclass
class RefreshStats:
    cached: int = 0
    incremental: int = 0
    full: int = 0
    failed: int = 0


class MarketDataStore:
    def __init__(self, root: Path, downloader: Downloader | None = None) -> None:
        self.root = root
        self.downloader = downloader or YahooBatchDownloader()
        self._fresh: set[tuple[str, str]] = set()

    def path(self, symbol: str, interval: str) -> Path:
        return self.root / interval / f"{symbol}.parquet"

    def load(self, symbol: str, interval: str) -> pd.DataFrame:
        path = self.path(symbol, interval)
        if not path.exists():
            return empty_bars()
        return pd.read_parquet(path)

    def save(self, symbol: str, interval: str, df: pd.DataFrame) -> None:
        path = self.path(symbol, interval)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)

    def is_recent(self, symbol: str, interval: str, max_age: timedelta) -> bool:
        path = self.path(symbol, interval)
        if not path.exists():
            return False
        return time.time() - path.stat().st_mtime < max_age.total_seconds()

    def refresh(
        self,
        symbols: list[str],
        interval: str,
        on_progress: Callable[[int], None] | None = None,
        max_age: timedelta | None = None,
    ) -> RefreshStats:
        """Bring the cache for ``symbols`` up to date.

        Each symbol is refreshed once per store instance; with ``max_age`` symbols whose cache
        file was written more recently than that are skipped as well.
        """
        spec = INTERVALS[interval]
        stats = RefreshStats()
        pending = [
            symbol
            for symbol in symbols
            if (interval, symbol) not in self._fresh
            and not (max_age is not None and self.is_recent(symbol, interval, max_age))
        ]
        stats.cached = len(symbols) - len(pending)

        now = pd.Timestamp.now(tz="UTC").tz_localize(None)
        groups: dict[str, list[str]] = defaultdict(list)
        cached: dict[str, pd.DataFrame] = {}
        full: list[str] = []

        for symbol in pending:
            df = self.load(symbol, interval)
            if df.empty:
                full.append(symbol)
                continue
            last = df.index[-1]
            last = last.tz_convert(None) if last.tzinfo is not None else last
            start = (last - spec.overlap).normalize()
            if spec.max_history is not None and now - start > spec.max_history:
                full.append(symbol)
                continue
            cached[symbol] = df
            groups[start.strftime("%Y-%m-%d")].append(symbol)

        for start, group in groups.items():
            fresh = self.downloader(group, interval, start=start)
            for symbol in group:
                new = fresh.get(symbol)
                if new is None or new.empty:
                    # Keep the cached history; Yahoo occasionally drops symbols for a day.
                    self._fresh.add((interval, symbol))
                    stats.failed += 1
                else:
                    merged = merge_bars(cached[symbol], new)
                    if merged is None:
                        full.append(symbol)
                        continue
                    self.save(symbol, interval, merged)
                    self._fresh.add((interval, symbol))
                    stats.incremental += 1
                if on_progress:
                    on_progress(1)

        if full:
            fresh = self.downloader(full, interval, period=spec.full_period)
            missing = [symbol for symbol in full if symbol not in fresh]
            if missing and spec.fallback_period:
                fresh.update(self.downloader(missing, interval, period=spec.fallback_period))
            for symbol in full:
                new = fresh.get(symbol)
                if new is None or new.empty:
                    stats.failed += 1
                else:
                    self.save(symbol, interval, new)
                    stats.full += 1
                self._fresh.add((interval, symbol))
                if on_progress:
                    on_progress(1)

        return stats
