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

from .data import YahooFinanceProvider, resample_to_4h
from .indicators import (
    daily_52_week_levels,
    moving_averages,
    percentile_ratings,
    weighted_momentum_score,
)
from .models import ScanResult, Timeframe
from .rules import build_result_frame

console = Console()


@dataclass
class ScannerConfig:
    rs_threshold: float = 70.0
    min_score: int = 7
    slope_daily: int = 22
    slope_4h: int = 33


class Scanner:
    def __init__(
        self,
        provider: YahooFinanceProvider | None = None,
        config: ScannerConfig | None = None,
    ) -> None:
        self.provider = provider or YahooFinanceProvider()
        self.config = config or ScannerConfig()

    def scan(self, symbols: list[str], timeframe: Timeframe) -> list[ScanResult]:
        console.rule("[bold cyan]MINERVINI NSE SCANNER[/bold cyan]")
        console.print(f"  [bold]Timeframe:[/bold] {timeframe.value.upper()}")
        console.print(f"  [bold]Universe:[/bold] {len(symbols):,} symbols")
        console.print()

        raw: list[tuple[str, pd.DataFrame, pd.DataFrame, float]] = []
        skipped = 0
        min_periods = (
            200 + self.config.slope_4h
            if timeframe is Timeframe.FOUR_HOUR
            else 200 + self.config.slope_daily
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Downloading market data",
                total=len(symbols),
            )
            for symbol in symbols:
                try:
                    progress.update(
                        task,
                        description=f"[cyan]Downloading {symbol}",
                    )
                    daily = self.provider.daily(symbol)
                    if len(daily) < 252:
                        skipped += 1
                        continue

                    daily = daily_52_week_levels(daily)
                    raw_rs = weighted_momentum_score(daily)

                    if timeframe is Timeframe.DAILY:
                        tf = daily.copy()
                    else:
                        hourly = self.provider.hourly(symbol)
                        tf = resample_to_4h(hourly)

                    if len(tf) < min_periods:
                        skipped += 1
                        continue

                    tf = moving_averages(tf)
                    raw.append((symbol, tf, daily, raw_rs))
                except Exception as exc:
                    skipped += 1
                    console.print(f"[yellow]Warning:[/yellow] {symbol}: {exc}")
                finally:
                    progress.advance(task)

        console.print()
        console.rule("[bold cyan]CALCULATING RELATIVE STRENGTH[/bold cyan]")
        ratings = percentile_ratings({symbol: raw_rs for symbol, _, _, raw_rs in raw})

        slope_periods = (
            self.config.slope_daily if timeframe is Timeframe.DAILY else self.config.slope_4h
        )

        results: list[ScanResult] = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Applying Minervini rules", total=len(raw))
            for symbol, tf, daily, _ in raw:
                rs_rating = ratings.get(symbol, 0.0)
                result = build_result_frame(
                    tf,
                    daily,
                    rs_rating,
                    self.config.rs_threshold,
                    slope_periods,
                )
                results.append(
                    ScanResult(
                        symbol=symbol,
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
                    )
                )
                progress.advance(task)

        results.sort(key=lambda item: (item.score, item.rs_rating), reverse=True)
        nine = sum(result.score == 9 for result in results)
        eight = sum(result.score == 8 for result in results)
        seven = sum(result.score == 7 for result in results)
        shortlisted = sum(result.score >= self.config.min_score for result in results)

        console.print()
        console.rule("[bold green]SCAN COMPLETE[/bold green]")
        console.print(f"  Stocks scanned       : [bold]{len(symbols):,}[/bold]")
        console.print(f"  Valid results        : [bold]{len(results):,}[/bold]")
        console.print(f"  Skipped / invalid    : [bold]{skipped:,}[/bold]")
        console.print(f"  [green]9/9 candidates       : {nine:,}[/green]")
        console.print(f"  [green]8/9 candidates       : {eight:,}[/green]")
        console.print(f"  [yellow]7/9 candidates       : {seven:,}[/yellow]")
        console.print(
            f"  [bold cyan]Shortlisted (>={self.config.min_score}/9) : {shortlisted:,}[/bold cyan]"
        )
        console.print()
        return results


def results_to_frame(results: list[ScanResult]) -> pd.DataFrame:
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
            }
        )

    return pd.DataFrame(rows)


def save_results(
    results: list[ScanResult],
    output_dir: Path,
    timeframe: Timeframe,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    df = results_to_frame(results)

    csv_path = output_dir / f"minervini_{timeframe.value}.csv"
    xlsx_path = output_dir / f"minervini_{timeframe.value}.xlsx"

    df.to_csv(csv_path, index=False)
    df.to_excel(xlsx_path, index=False)

    return csv_path, xlsx_path
