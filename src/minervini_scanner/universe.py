"""The scan universe: every NSE equity in the regular (``EQ``) series.

NSE publishes the full listing in ``EQUITY_L.csv``. ``BE``/``BZ`` stocks (trade-for-trade or
non-compliant) are left out: they are not tradable as normal swing candidates.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

EQUITY_LIST_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
REGULAR_SERIES = "EQ"


def parse_equity_list(text: str) -> list[str]:
    """Symbols of the regular series, sorted and de-duplicated."""
    reader = csv.DictReader(io.StringIO(text))
    symbols: set[str] = set()
    for row in reader:
        cells = {(key or "").strip().upper(): (value or "").strip() for key, value in row.items()}
        symbol = cells.get("SYMBOL", "").upper()
        if symbol and cells.get("SERIES", "").upper() == REGULAR_SERIES:
            symbols.add(symbol)
    return sorted(symbols)


def download_equity_symbols(url: str = EQUITY_LIST_URL, timeout: float = 30) -> list[str]:
    # NSE rejects requests without a browser-like user agent.
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8", errors="replace")
    symbols = parse_equity_list(text)
    if not symbols:
        raise ValueError("NSE equity list contained no EQ-series symbols")
    return symbols


def save_symbols(symbols: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["SYMBOL"])
        writer.writerows([symbol] for symbol in symbols)
