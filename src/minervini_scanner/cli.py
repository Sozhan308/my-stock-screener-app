from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from .config import get_settings
from .data import load_symbols
from .fno import download_lot_sizes, load_lot_sizes, save_lot_sizes
from .journal import check_trades, load_trades
from .models import Timeframe
from .notify import DigestFilters, build_digest, send_telegram
from .scanner import Scanner, ScannerConfig, save_results
from .setups import SetupResult
from .store import MarketDataStore, YahooBatchDownloader
from .universe import download_equity_symbols, save_symbols
from .watchlist import WatchlistStore

app = typer.Typer(help="Minervini NSE scanner.")


def _scanner() -> Scanner:
    settings = get_settings()
    store = MarketDataStore(
        settings.data_dir,
        YahooBatchDownloader(pause=settings.request_delay),
    )
    return Scanner(
        store=store,
        config=ScannerConfig(
            rs_threshold=settings.rs_threshold,
            min_score=settings.min_score,
            min_traded_value_cr=settings.min_traded_value_cr,
            min_price=settings.min_price,
        ),
        lot_sizes=load_lot_sizes(settings.fno_file),
    )


def _run_scan(
    scanner: Scanner,
    timeframe: Timeframe,
    symbols_file: Path,
) -> tuple[Path, Path]:
    """Run a scan for a single timeframe and save the results."""
    settings = get_settings()

    symbols = load_symbols(symbols_file)
    results = scanner.scan(symbols, timeframe)

    csv_path, xlsx_path = save_results(
        results,
        settings.output_dir,
        timeframe,
        scanner.config,
    )

    shortlisted = [result for result in results if result.score >= settings.min_score]

    typer.echo(f"Universe: {len(symbols)}")
    typer.echo(f"Valid results: {len(results)}")
    typer.echo(f"Skipped / invalid: {len(symbols) - len(results)}")
    typer.echo(f"Shortlisted (>= {settings.min_score}/9): {len(shortlisted)}")
    typer.echo(f"CSV: {csv_path}")
    typer.echo(f"XLSX: {xlsx_path}")

    return csv_path, xlsx_path


@app.command()
def scan(
    timeframe: str = typer.Option("daily", "--timeframe", "-t"),
    symbols_file: Path = typer.Option(  # noqa: B008
        Path("nse_symbols.csv"),
        "--symbols-file",
    ),
) -> None:
    """Scan NSE symbols and export results."""
    try:
        selected = Timeframe(timeframe)
    except ValueError as exc:
        raise typer.BadParameter("Use 'daily' or '4h'.") from exc

    _run_scan(_scanner(), selected, symbols_file)


@app.command()
def update(
    symbols_file: Path = typer.Option(  # noqa: B008
        Path("nse_symbols.csv"),
        "--symbols-file",
    ),
) -> None:
    """Run the complete Daily and 4H market-data update."""
    typer.echo("Starting complete market scan update...")
    typer.echo()

    scanner = _scanner()
    daily_csv, daily_xlsx = _run_scan(
        scanner,
        Timeframe.DAILY,
        symbols_file,
    )

    typer.echo()
    typer.echo("Daily scan completed.")
    typer.echo()

    four_hour_csv, four_hour_xlsx = _run_scan(
        scanner,
        Timeframe.FOUR_HOUR,
        symbols_file,
    )

    typer.echo()
    typer.echo("4H scan completed.")
    typer.echo()

    output_files = [
        daily_csv,
        daily_xlsx,
        four_hour_csv,
        four_hour_xlsx,
    ]

    invalid = [path for path in output_files if not path.exists() or path.stat().st_size == 0]

    if invalid:
        typer.echo("Update failed: one or more output files are invalid.")
        for path in invalid:
            typer.echo(f"  - {path}")
        raise typer.Exit(code=1)

    typer.echo("──────────────────── UPDATE COMPLETE ────────────────────")
    typer.echo("Daily and 4H scan results generated successfully.")
    typer.echo()

    for path in output_files:
        typer.echo(f"  {path}")


def _describe(result: SetupResult) -> str:
    if result.base is None:
        return result.stage.value
    return (
        f"{result.stage.value} ({result.setup_type}, score {result.score}, "
        f"pivot {result.base.pivot:,.2f})"
    )


@app.command("journal-check")
def journal_check(
    trades_file: Path = typer.Argument(  # noqa: B008
        ...,
        help="CSV with 'symbol' and 'date' columns, one row per trade.",
    ),
) -> None:
    """Show whether the setup detector flagged past trades before or on the entry day."""
    trades = load_trades(trades_file)
    checks = check_trades(_scanner().store, trades)

    table = Table(title="Setup detector vs. past trades")
    for column in ("Symbol", "Date", "Daily (prior close)", "Daily (entry close)", "4H (prior)"):
        table.add_column(column)
    table.add_column("4H (entry day)")
    table.add_column("Flagged")

    for check in checks:
        table.add_row(
            check.symbol,
            f"{check.date:%Y-%m-%d}",
            _describe(check.daily_before),
            _describe(check.daily_on),
            _describe(check.four_hour_before),
            _describe(check.four_hour_on),
            "yes" if check.detected else "no",
        )

    console = Console()
    console.print(table)
    detected = sum(check.detected for check in checks)
    console.print(f"Flagged as Ready/Breakout/Recent breakout: {detected} of {len(checks)}")


@app.command("update-fno")
def update_fno() -> None:
    """Refresh the F&O lot-size snapshot from NSE."""
    settings = get_settings()
    lots = download_lot_sizes()
    save_lot_sizes(lots, settings.fno_file)
    typer.echo(f"Saved {len(lots)} F&O stocks to {settings.fno_file}")


@app.command("update-universe")
def update_universe(
    symbols_file: Path = typer.Option(  # noqa: B008
        Path("nse_symbols.csv"),
        help="CSV to overwrite with every NSE EQ-series symbol.",
    ),
) -> None:
    """Refresh the scan universe (all NSE EQ-series stocks) from NSE."""
    symbols = download_equity_symbols()
    save_symbols(symbols, symbols_file)
    typer.echo(f"Saved {len(symbols)} NSE EQ symbols to {symbols_file}")


def _read_scan(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


@app.command()
def notify(
    token: str = typer.Option("", envvar="TELEGRAM_BOT_TOKEN", show_default=False),
    chat_id: str = typer.Option("", envvar="TELEGRAM_CHAT_ID", show_default=False),
    min_rs: float = typer.Option(60.0, help="Minimum RS rating for the digest."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print instead of sending."),
) -> None:
    """Send the evening setup digest to Telegram (reads the latest scan CSVs)."""
    settings = get_settings()
    messages = build_digest(
        _read_scan(settings.output_dir / "minervini_daily.csv"),
        _read_scan(settings.output_dir / "minervini_4h.csv"),
        WatchlistStore(settings.watchlist_db).list_symbols(),
        as_of=datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y"),
        filters=DigestFilters(min_score=settings.min_score, min_rs=min_rs),
    )

    if dry_run:
        typer.echo("\n\n---\n\n".join(messages))
        return
    if not token or not chat_id:
        typer.echo("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set; skipping Telegram digest.")
        return

    send_telegram(token, chat_id, messages)
    typer.echo(f"Sent {len(messages)} Telegram message(s).")


@app.command()
def api(
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Start the FastAPI backend."""
    import uvicorn

    uvicorn.run(
        "minervini_scanner.api:app",
        host=host,
        port=port,
        reload=True,
    )
