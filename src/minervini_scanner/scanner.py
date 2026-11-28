from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .data import complete_daily_from_hourly, resample_to_4h
from .indicators import (
    daily_52_week_levels,
    moving_averages,
    percentile_ratings,
    weighted_momentum_score,
)
from .models import ScanResult, Timeframe
from .rules import build_result_frame
from .setups import (
    ACTIONABLE_STAGES,
    DAILY_PRESETS,
    FOUR_HOUR_PRESETS,
    HOURLY_PRESETS,
    STAGE_PRIORITY,
    SetupResult,
    Stage,
    detect_best_setup,
)
from .store import MarketDataStore

console = Console()


@dataclass
class ScannerConfig:
    rs_threshold: float = 70.0
    min_score: int = 7
    slope_daily: int = 22
    slope_4h: int = 33
    min_traded_value_cr: float = 5.0
    min_price: float = 30.0
    # Also run the 1H power-play check (needs hourly bars) and report it as a hint.
    hourly_hint: bool = True


@dataclass
class _Analysed:
    symbol: str
    tf: pd.DataFrame
    daily: pd.DataFrame
    raw_rs: float
    setup: SetupResult
    hourly_setup: SetupResult | None
    traded_value_cr: float


def traded_value_cr(daily: pd.DataFrame) -> float:
    """50-day average traded value in crore rupees."""
    return float((daily["Close"] * daily["Volume"]).tail(50).mean() / 1e7)


def _progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
    )


class Scanner:
    def __init__(
        self,
        store: MarketDataStore,
        config: ScannerConfig | None = None,
        lot_sizes: dict[str, int] | None = None,
    ) -> None:
        self.store = store
        self.config = config or ScannerConfig()
        self.lot_sizes = lot_sizes or {}

    def _refresh(self, symbols: list[str], interval: str, label: str) -> None:
        with _progress() as progress:
            task = progress.add_task(f"[cyan]{label}", total=len(symbols))
            stats = self.store.refresh(
                symbols,
                interval,
                on_progress=lambda count: progress.advance(task, count),
            )
            progress.update(task, completed=len(symbols))
        console.print(
            f"  {interval}: {stats.incremental:,} updated, {stats.full:,} full downloads, "
            f"{stats.cached:,} already fresh, {stats.failed:,} unavailable"
        )

    def _is_liquid(self, daily: pd.DataFrame) -> bool:
        closes = daily["Close"].dropna()
        if closes.empty:
            return False
        return bool(
            traded_value_cr(daily) >= self.config.min_traded_value_cr
            and float(closes.iloc[-1]) >= self.config.min_price
        )

    def scan(self, symbols: list[str], timeframe: Timeframe) -> list[ScanResult]:
        console.rule("[bold cyan]MINERVINI NSE SCANNER[/bold cyan]")
        console.print(f"  [bold]Timeframe:[/bold] {timeframe.value.upper()}")
        console.print(f"  [bold]Universe:[/bold] {len(symbols):,} symbols")
        console.print()

        use_hourly = timeframe is Timeframe.FOUR_HOUR or self.config.hourly_hint
        self._refresh(symbols, "1d", "Updating daily bars")

        # Hourly bars (1H hint and 4H candles) are only fetched for liquid stocks, which keeps
        # a universe of every NSE equity quick to refresh.
        liquid = {s for s in symbols if self._is_liquid(self.store.load(s, "1d"))}
        console.print(f"  Liquid stocks: {len(liquid):,} of {len(symbols):,}")
        if use_hourly:
            self._refresh([s for s in symbols if s in liquid], "1h", "Updating hourly bars")

        presets = DAILY_PRESETS if timeframe is Timeframe.DAILY else FOUR_HOUR_PRESETS
        raw: list[_Analysed] = []
        skipped = 0
        min_periods = (
            200 + self.config.slope_4h
            if timeframe is Timeframe.FOUR_HOUR
            else 200 + self.config.slope_daily
        )

        with _progress() as progress:
            task = progress.add_task("[cyan]Analysing trend and setups", total=len(symbols))
            for symbol in symbols:
                try:
                    hourly = (
                        self.store.load(symbol, "1h") if use_hourly and symbol in liquid else None
                    )
                    daily = complete_daily_from_hourly(self.store.load(symbol, "1d"), hourly)
                    if len(daily) < 252:
                        skipped += 1
                        continue

                    daily = daily_52_week_levels(daily)
                    raw_rs = weighted_momentum_score(daily)

                    if timeframe is Timeframe.DAILY:
                        tf = daily.copy()
                    elif hourly is None or hourly.empty:
                        skipped += 1
                        continue
                    else:
                        tf = resample_to_4h(hourly)

                    if len(tf) < min_periods:
                        skipped += 1
                        continue

                    tf = moving_averages(tf)
                    setup = detect_best_setup(tf, presets)
                    traded_value = traded_value_cr(daily)
                    hourly_setup = (
                        detect_best_setup(hourly, HOURLY_PRESETS)
                        if self.config.hourly_hint and hourly is not None and not hourly.empty
                        else None
                    )
                    raw.append(
                        _Analysed(symbol, tf, daily, raw_rs, setup, hourly_setup, traded_value)
                    )
                except Exception as exc:
                    skipped += 1
                    console.print(f"[yellow]Warning:[/yellow] {symbol}: {exc}")
                finally:
                    progress.advance(task)

        # RS is a percentile within the liquid universe, so adding thin microcaps does not move it.
        ratings = percentile_ratings(
            {item.symbol: item.raw_rs for item in raw},
            reference={item.symbol for item in raw if item.symbol in liquid},
        )

        slope_periods = (
            self.config.slope_daily if timeframe is Timeframe.DAILY else self.config.slope_4h
        )

        results: list[ScanResult] = []
        for item in raw:
            rs_rating = ratings.get(item.symbol, 0.0)
            result = build_result_frame(
                item.tf,
                item.daily,
                rs_rating,
                self.config.rs_threshold,
                slope_periods,
            )
            results.append(
                ScanResult(
                    symbol=item.symbol,
                    price=result["price"],
                    ma50=result["ma50"],
                    ma150=result["ma150"],
                    ma200=result["ma200"],
                    ma200_slope_pct=result["ma200_slope_pct"],
                    high_52w=result["high_52w"],
                    low_52w=result["low_52w"],
                    pct_above_52w_low=result["pct_above_52w_low"],
                    pct_below_52w_high=result["pct_below_52w_high"],
                    rs_rating=rs_rating,
                    checklist=result["checklist"],
                    timeframe=timeframe,
                    setup=item.setup,
                    avg_traded_value_cr=item.traded_value_cr,
                    hourly_setup=item.hourly_setup,
                    lot_size=self.lot_sizes.get(item.symbol),
                )
            )

        results.sort(
            key=lambda item: (
                STAGE_PRIORITY[item.setup.stage],
                -item.setup.score,
                -item.score,
                -item.rs_rating,
            )
        )
        shortlisted = [result for result in results if result.score >= self.config.min_score]
        actionable = [result for result in shortlisted if result.setup.stage in ACTIONABLE_STAGES]

        def count(stage: Stage) -> int:
            return sum(result.setup.stage is stage for result in shortlisted)

        console.print()
        console.rule("[bold green]SCAN COMPLETE[/bold green]")
        console.print(f"  Stocks scanned       : [bold]{len(symbols):,}[/bold]")
        console.print(f"  Valid results        : [bold]{len(results):,}[/bold]")
        console.print(f"  Skipped / invalid    : [bold]{skipped:,}[/bold]")
        console.print(
            f"  [bold cyan]Trend template (>={self.config.min_score}/9) : "
            f"{len(shortlisted):,}[/bold cyan]"
        )
        console.print(f"  [green]  Breakout today     : {count(Stage.BREAKOUT):,}[/green]")
        console.print(f"  [green]  Ready (near pivot) : {count(Stage.READY):,}[/green]")
        console.print(f"  [green]  Recent breakout    : {count(Stage.RECENT_BREAKOUT):,}[/green]")
        console.print(f"  [yellow]  Forming            : {count(Stage.FORMING):,}[/yellow]")
        console.print(f"  [bold green]Actionable setups    : {len(actionable):,}[/bold green]")
        console.print()
        return results


def _date(value: pd.Timestamp | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.tz_convert("Asia/Kolkata")
    if value.hour == 0 and value.minute == 0:
        return value.strftime("%Y-%m-%d")
    return value.strftime("%Y-%m-%d %H:%M")


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(float(value), digits)


def setup_columns(setup: SetupResult) -> dict:
    base = setup.base
    shakeout = base.shakeout if base else None
    return {
        "Stage": setup.stage.value,
        "Setup": setup.setup_type,
        "Setup Score": setup.score,
        "Pivot": _round(base.pivot) if base else None,
        "Stop": _round(base.stop) if base else None,
        "Risk %": _round(setup.risk_pct),
        "% From Pivot": _round(setup.pct_from_pivot),
        "Entry Zone": base.entry_zone.value if base else None,
        "Base Start": _date(base.start_date) if base else None,
        "Base Bars": base.bars if base else None,
        "Base Depth %": _round(base.depth_pct) if base else None,
        "Prior Rally %": _round(base.rally_pct, 1) if base else None,
        "Contractions": (
            " / ".join(f"{c.depth_pct:.1f}" for c in base.contractions) if base else None
        ),
        "Shakeout": _date(shakeout.low_date) if shakeout else None,
        "Volume Dry-up": _round(setup.volume_dryup),
        "Tightness %": _round(setup.tightness_pct),
        "Breakout Date": _date(setup.breakout_date),
        "Breakout Volume x": _round(setup.breakout_volume_ratio),
        "Setup Notes": "; ".join(setup.notes) or None,
    }


def hourly_columns(setup: SetupResult | None) -> dict:
    base = setup.base if setup else None
    return {
        "1H Stage": setup.stage.value if setup else None,
        "1H Pivot": _round(base.pivot) if base else None,
        "1H % From Pivot": _round(setup.pct_from_pivot) if setup else None,
        "1H Setup Score": setup.score if setup and base else None,
    }


def results_to_frame(
    results: list[ScanResult],
    config: ScannerConfig | None = None,
) -> pd.DataFrame:
    config = config or ScannerConfig()
    rows = []

    for item in results:
        rows.append(
            {
                "Symbol": item.symbol,
                "Timeframe": item.timeframe.value,
                "Price": item.price,
                "MA50": item.ma50,
                "MA150": item.ma150,
                "MA200": item.ma200,
                "MA200 slope %": item.ma200_slope_pct,
                "52W High": item.high_52w,
                "52W Low": item.low_52w,
                "% Above 52W Low": item.pct_above_52w_low,
                "% Below 52W High": item.pct_below_52w_high,
                "RS Rating": item.rs_rating,
                "Score": item.score,
                "TradingView": item.tradingview_url,
                "P > MA50": item.checklist.price_above_ma50,
                "P > MA150": item.checklist.price_above_ma150,
                "P > MA200": item.checklist.price_above_ma200,
                "MA50 > MA150": item.checklist.ma50_above_ma150,
                "MA150 > MA200": item.checklist.ma150_above_ma200,
                "MA200 Rising": item.checklist.ma200_rising,
                "25% Above 52W Low": item.checklist.above_52w_low_25,
                "Within 25% 52W High": item.checklist.within_25pct_52w_high,
                "RS > Threshold": item.checklist.rs_above_threshold,
                **setup_columns(item.setup),
                **hourly_columns(item.hourly_setup),
                "F&O": item.lot_size is not None,
                "Lot Size": item.lot_size,
                "Avg Value (Cr)": round(item.avg_traded_value_cr, 2),
                "Liquid": (
                    item.avg_traded_value_cr >= config.min_traded_value_cr
                    and item.price >= config.min_price
                ),
            }
        )

    return pd.DataFrame(rows)


def save_results(
    results: list[ScanResult],
    output_dir: Path,
    timeframe: Timeframe,
    config: ScannerConfig | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    df = results_to_frame(results, config)

    csv_path = output_dir / f"minervini_{timeframe.value}.csv"
    xlsx_path = output_dir / f"minervini_{timeframe.value}.xlsx"

    df.to_csv(csv_path, index=False)
    df.to_excel(xlsx_path, index=False)

    return csv_path, xlsx_path
