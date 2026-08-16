from pathlib import Path

import typer

from .config import get_settings
from .data import YahooFinanceProvider, load_symbols
from .models import Timeframe
from .scanner import Scanner, ScannerConfig, save_results

app = typer.Typer(help="Minervini NSE scanner.")


@app.command()
def scan(
    timeframe: str = typer.Option("daily", "--timeframe", "-t"),
    symbols_file: Path = typer.Option(  # noqa: B008
        Path("nse_symbols.csv"),
        "--symbols-file",
    ),
) -> None:
    """Scan NSE symbols and export results."""
    settings = get_settings()

    try:
        selected = Timeframe(timeframe)
    except ValueError as exc:
        raise typer.BadParameter("Use 'daily' or '4h'.") from exc

    symbols = load_symbols(symbols_file)

    scanner = Scanner(
        provider=YahooFinanceProvider(settings.request_delay),
        config=ScannerConfig(
            rs_threshold=settings.rs_threshold,
        ),
    )

    results = scanner.scan(symbols, selected)
    csv_path, xlsx_path = save_results(
        results,
        settings.output_dir,
        selected,
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
