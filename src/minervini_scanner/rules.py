from __future__ import annotations

import pandas as pd

from .models import Checklist


def evaluate_checklist(
    timeframe_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    rs_rating: float,
    rs_threshold: float = 70.0,
    slope_periods: int = 22,
) -> Checklist:
    current = timeframe_df.iloc[-1]
    daily = daily_df.iloc[-1]

    ma200_previous = timeframe_df["MA200"].iloc[-1 - slope_periods]

    price = float(current["Close"])
    ma50 = float(current["MA50"])
    ma150 = float(current["MA150"])
    ma200 = float(current["MA200"])

    high_52w = float(daily["52W_HIGH"])
    low_52w = float(daily["52W_LOW"])

    pct_above_low = (price / low_52w - 1) * 100
    pct_below_high = (high_52w / price - 1) * 100

    return Checklist(
        price_above_ma50=price > ma50,
        price_above_ma150=price > ma150,
        price_above_ma200=price > ma200,
        ma50_above_ma150=ma50 > ma150,
        ma150_above_ma200=ma150 > ma200,
        ma200_rising=ma200 > float(ma200_previous),
        above_52w_low_25=pct_above_low >= 25,
        within_25pct_52w_high=pct_below_high <= 25,
        rs_above_threshold=rs_rating >= rs_threshold,
    )


def build_result_frame(
    timeframe_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    rs_rating: float,
    rs_threshold: float,
    slope_periods: int,
) -> dict:
    current = timeframe_df.iloc[-1]
    daily = daily_df.iloc[-1]

    ma200_previous = float(timeframe_df["MA200"].iloc[-1 - slope_periods])
    ma200 = float(current["MA200"])
    price = float(current["Close"])
    high_52w = float(daily["52W_HIGH"])
    low_52w = float(daily["52W_LOW"])

    return {
        "price": price,
        "ma50": float(current["MA50"]),
        "ma150": float(current["MA150"]),
        "ma200": ma200,
        "ma200_slope_pct": (ma200 / ma200_previous - 1) * 100,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "pct_above_52w_low": (price / low_52w - 1) * 100,
        "pct_below_52w_high": (high_52w / price - 1) * 100,
        "checklist": evaluate_checklist(
            timeframe_df,
            daily_df,
            rs_rating,
            rs_threshold,
            slope_periods,
        ),
    }
