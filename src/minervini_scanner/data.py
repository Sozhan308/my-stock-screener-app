from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import yfinance as yf


def load_symbols(path: Path) -> list[str]:
    df = pd.read_csv(path)
    column = next(
        (col for col in df.columns if col.upper() == "SYMBOL"),
        None,
    )
    if column is None:
        raise ValueError("Symbol CSV must contain a SYMBOL column")

    return df[column].dropna().astype(str).str.strip().str.upper().drop_duplicates().tolist()


class YahooFinanceProvider:
    def __init__(self, request_delay: float = 0.15) -> None:
        self.request_delay = request_delay

    def daily(self, symbol: str) -> pd.DataFrame:
        return self._download(symbol, period="3y", interval="1d")

    def hourly(self, symbol: str) -> pd.DataFrame:
        return self._download(symbol, period="2y", interval="1h")

    def _download(
        self,
        symbol: str,
        *,
        period: str,
        interval: str,
    ) -> pd.DataFrame:
        time.sleep(self.request_delay)

        df = yf.download(
            f"{symbol}.NS",
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )

        if df.empty:
            return df

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])


def resample_to_4h(hourly: pd.DataFrame) -> pd.DataFrame:
    if hourly.empty:
        return hourly

    df = hourly.copy()
    df.index = pd.to_datetime(df.index)

    if df.index.tz is not None:
        df.index = df.index.tz_convert("Asia/Kolkata")

    df = df[df.index.dayofweek < 5]
    df = df.between_time("09:15", "15:30")

    if df.empty:
        return df

    result = (
        df.resample("4h", origin="start_day", offset="9h15min")
        .agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        )
        .dropna(subset=["Open", "High", "Low", "Close"])
    )

    return result[(result.index.hour >= 9) & (result.index.hour <= 13)]
