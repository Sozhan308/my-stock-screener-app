from dataclasses import dataclass
from enum import StrEnum


class Timeframe(StrEnum):
    DAILY = "daily"
    FOUR_HOUR = "4h"


@dataclass(frozen=True)
class Checklist:
    price_above_ma50: bool
    price_above_ma150: bool
    price_above_ma200: bool
    ma50_above_ma150: bool
    ma150_above_ma200: bool
    ma200_rising: bool
    above_52w_low_25: bool
    within_25pct_52w_high: bool
    rs_above_threshold: bool

    @property
    def score(self) -> int:
        return sum(
            (
                self.price_above_ma50,
                self.price_above_ma150,
                self.price_above_ma200,
                self.ma50_above_ma150,
                self.ma150_above_ma200,
                self.ma200_rising,
                self.above_52w_low_25,
                self.within_25pct_52w_high,
                self.rs_above_threshold,
            )
        )


@dataclass(frozen=True)
class ScanResult:
    symbol: str
    price: float
    ma50: float
    ma150: float
    ma200: float
    ma200_slope_pct: float
    high_52w: float
    low_52w: float
    pct_above_52w_low: float
    pct_below_52w_high: float
    rs_rating: float
    checklist: Checklist
    timeframe: Timeframe

    @property
    def score(self) -> int:
        return self.checklist.score

    @property
    def tradingview_url(self) -> str:
        return f"https://www.tradingview.com/symbols/{self.symbol}/?exchange=NSE"
