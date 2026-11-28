"""NSE F&O (stock derivatives) eligibility and lot sizes.

NSE publishes the current lot sizes per underlying in ``fo_mktlots.csv``. A snapshot is kept in
the repository (``data/fno_lots.csv``) so scans never depend on NSE being reachable.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

FNO_LOTS_URL = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"
STOCK_SECTION_MARKER = "derivatives on individual securities"


def parse_lot_sizes(text: str) -> dict[str, int]:
    """Map stock symbol -> nearest-expiry lot size; index derivatives are skipped."""
    lots: dict[str, int] = {}
    in_stocks = False
    for row in csv.reader(io.StringIO(text)):
        cells = [cell.strip() for cell in row]
        if not cells or not cells[0]:
            continue
        if cells[0].lower() == STOCK_SECTION_MARKER:
            in_stocks = True
            continue
        if not in_stocks or len(cells) < 3:
            continue
        symbol = cells[1].upper()
        lot = next((cell for cell in cells[2:] if cell.isdigit()), None)
        if symbol and lot:
            lots[symbol] = int(lot)
    return lots


def download_lot_sizes(url: str = FNO_LOTS_URL, timeout: float = 30) -> dict[str, int]:
    # NSE rejects requests without a browser-like user agent.
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8", errors="replace")
    lots = parse_lot_sizes(text)
    if not lots:
        raise ValueError("NSE lot-size file contained no stock derivatives")
    return lots


def save_lot_sizes(lots: dict[str, int], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["SYMBOL", "LOT_SIZE"])
        for symbol in sorted(lots):
            writer.writerow([symbol, lots[symbol]])


def load_lot_sizes(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    with path.open(newline="") as handle:
        return {row["SYMBOL"]: int(row["LOT_SIZE"]) for row in csv.DictReader(handle)}
