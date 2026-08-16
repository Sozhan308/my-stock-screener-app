from pathlib import Path

import typer

from .config import get_settings
from .data import YahooFinanceProvider, load_symbols
from .models import Timeframe
from .scanner import Scanner, ScannerConfig, save_results

app = typer.Typer(help="Minervini NSE scanner.")


def _run_scan(
    timeframe: Timeframe,
    symbols_file: Path,
) -> tuple[Path, Path]:
    """Run a scan for a single timeframe and save the results."""
    settings = get_settings()

    symbols = load_symbols(symbols_file)

    scanner = Scanner(
        provider=YahooFinanceProvider(settings.request_delay),
        config=ScannerConfig(
            rs_threshold=settings.rs_threshold,
            min_score=settings.min_score,
        ),
    )

    results = scanner.scan(symbols, timeframe)

    csv_path, xlsx_path = save_results(
        results,
        settings.output_dir,
        timeframe,
    )

    shortlisted = [result for result in results if result.score >= settings.min_score]

    typer.echo(f"Universe: {len(symbols)}")
    typer.echo(f"Valid results: {len(results)}")
    typer.echo(f"Skipped / invalid: {len(symbols) - len(results)}")
    typer.echo(f"Shortlisted (>= {settings.min_score}/9): {len(shortlisted)}")
    typer.echo(f"Scanned: {len(results)}")
    typer.echo(f"Shortlisted: {len(shortlisted)}")
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

    _run_scan(selected, symbols_file)


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

    daily_csv, daily_xlsx = _run_scan(
        Timeframe.DAILY,
        symbols_file,
    )

    typer.echo()
    typer.echo("Daily scan completed.")
    typer.echo()

    four_hour_csv, four_hour_xlsx = _run_scan(
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
