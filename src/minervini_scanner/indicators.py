from __future__ import annotations

import numpy as np
import pandas as pd


def moving_averages(
    df: pd.DataFrame,
    periods: tuple[int, ...] = (50, 150, 200),
) -> pd.DataFrame:
    result = df.copy()
    for period in periods:
        result[f"MA{period}"] = result["Close"].rolling(period).mean()
    return result


def daily_52_week_levels(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["52W_HIGH"] = result["High"].rolling(252).max()
    result["52W_LOW"] = result["Low"].rolling(252).min()
    return result


def weighted_momentum_score(df: pd.DataFrame) -> float:
    close = df["Close"].dropna()
    if len(close) < 252:
        return np.nan

    current = float(close.iloc[-1])
    periods = (63, 126, 189, 252)
    weights = (0.20, 0.20, 0.20, 0.40)

    returns = [current / float(close.iloc[-period]) - 1 for period in periods]
    return float(sum(ret * weight for ret, weight in zip(returns, weights, strict=True)))


def percentile_ratings(raw_scores: dict[str, float]) -> dict[str, float]:
    valid = pd.Series(
        {symbol: score for symbol, score in raw_scores.items() if not np.isnan(score)}
    )
    if valid.empty:
        return {}

    return {
        symbol: float((valid <= score).mean() * 100)
        for symbol, score in raw_scores.items()
        if not np.isnan(score)
    }
