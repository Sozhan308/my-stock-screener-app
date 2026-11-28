import pandas as pd

from minervini_scanner.journal import check_trade
from minervini_scanner.store import MarketDataStore, merge_bars


def bars(start: str, closes: list[float]) -> pd.DataFrame:
    index = pd.bdate_range(start, periods=len(closes))
    return pd.DataFrame(
        {"Open": closes, "High": closes, "Low": closes, "Close": closes, "Volume": 1.0},
        index=index,
    )


def test_merge_appends_new_bars_and_replaces_last_cached_bar():
    cached = bars("2026-01-01", [10, 11, 12, 13])
    fresh = bars("2026-01-02", [11, 12, 13.5, 14])

    merged = merge_bars(cached, fresh)

    assert merged is not None
    assert merged["Close"].tolist() == [10, 11, 12, 13.5, 14]


def test_merge_detects_price_readjustment():
    cached = bars("2026-01-01", [10, 11, 12, 13])
    fresh = bars("2026-01-02", [5.5, 6, 6.5, 7])

    assert merge_bars(cached, fresh) is None


class FakeDownloader:
    def __init__(self, history: dict[str, pd.DataFrame]) -> None:
        self.history = history
        self.calls: list[tuple[list[str], str | None, str | None]] = []

    def __call__(self, symbols, interval, *, period=None, start=None):
        self.calls.append((symbols, period, start))
        result = {}
        for symbol in symbols:
            df = self.history[symbol]
            result[symbol] = df if start is None else df[df.index >= start]
        return result


def test_refresh_downloads_full_history_then_only_recent_bars(tmp_path):
    downloader = FakeDownloader({"AAA": bars("2026-01-01", list(range(1, 31)))})
    MarketDataStore(tmp_path, downloader).refresh(["AAA"], "1d")

    downloader.history["AAA"] = bars("2026-01-01", list(range(1, 33)))
    store = MarketDataStore(tmp_path, downloader)
    stats = store.refresh(["AAA"], "1d")

    assert stats.incremental == 1 and stats.full == 0
    assert downloader.calls[0][1] == "5y"
    assert downloader.calls[1][2] is not None
    assert len(store.load("AAA", "1d")) == 32


def test_refresh_redownloads_when_history_was_adjusted(tmp_path):
    downloader = FakeDownloader({"AAA": bars("2026-01-01", [float(x) for x in range(1, 31)])})
    MarketDataStore(tmp_path, downloader).refresh(["AAA"], "1d")

    downloader.history["AAA"] = bars("2026-01-01", [x / 2 for x in range(1, 32)])
    store = MarketDataStore(tmp_path, downloader)
    stats = store.refresh(["AAA"], "1d")

    assert stats.full == 1
    assert store.load("AAA", "1d")["Close"].iloc[0] == 0.5


def test_journal_check_handles_symbols_without_cached_data(tmp_path):
    check = check_trade(MarketDataStore(tmp_path), "NOPE", pd.Timestamp("2026-06-10"))

    assert not check.detected


def test_refresh_skips_recently_written_files(tmp_path):
    from datetime import timedelta

    downloader = FakeDownloader({"AAA": bars("2026-01-01", list(range(1, 31)))})
    MarketDataStore(tmp_path, downloader).refresh(["AAA"], "1d")

    stats = MarketDataStore(tmp_path, downloader).refresh(["AAA"], "1d", max_age=timedelta(hours=1))

    assert stats.cached == 1
    assert len(downloader.calls) == 1
