from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_symbols(path: Path) -> list[str]:
    df = pd.read_csv(path)
    column = next(
        (col for col in df.columns if col.upper() == "SYMBOL"),
        None,
    )
    if column is None:
        raise ValueError("Symbol CSV must contain a SYMBOL column")

    return df[column].dropna().astype(str).str.strip().str.upper().drop_duplicates().tolist()


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


def complete_daily_from_hourly(daily: pd.DataFrame, hourly: pd.DataFrame | None) -> pd.DataFrame:
    """Append sessions present in hourly bars but missing from daily bars.

    Yahoo often publishes the latest NSE daily bar late (prices empty, volume present), while the
    hourly bars for that session are already complete.
    """
    if hourly is None or hourly.empty:
        return daily

    index = pd.to_datetime(hourly.index)
    if index.tz is not None:
        index = index.tz_convert("Asia/Kolkata").tz_localize(None)
    bars = hourly.set_axis(index)
    bars = bars[bars.index.dayofweek < 5]

    sessions = bars.groupby(bars.index.normalize()).agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    )
    sessions.index.name = daily.index.name
    if daily.empty:
        return sessions

    missing = sessions[sessions.index > daily.index[-1]].copy()
    if missing.empty:
        return daily

    # Hourly bars miss auction/block volume (~25%), so rescale by this stock's recent ratio.
    common = daily.index.intersection(sessions.index)[-20:]
    hourly_share = (sessions.loc[common, "Volume"] / daily.loc[common, "Volume"]).median()
    if pd.notna(hourly_share) and 0 < hourly_share <= 1:
        missing["Volume"] = missing["Volume"] / hourly_share

    return pd.concat([daily, missing[daily.columns.intersection(missing.columns)]])
