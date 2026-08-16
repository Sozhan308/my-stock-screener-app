import sqlite3
from pathlib import Path


class WatchlistStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist (
                    symbol TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def list_symbols(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT symbol FROM watchlist ORDER BY symbol").fetchall()

        return [row["symbol"] for row in rows]

    def add(self, symbol: str) -> None:
        symbol = symbol.upper().strip()

        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)",
                (symbol,),
            )

    def remove(self, symbol: str) -> None:
        symbol = symbol.upper().strip()

        with self._connect() as connection:
            connection.execute(
                "DELETE FROM watchlist WHERE symbol = ?",
                (symbol,),
            )

    def contains(self, symbol: str) -> bool:
        symbol = symbol.upper().strip()

        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM watchlist WHERE symbol = ?",
                (symbol,),
            ).fetchone()

        return row is not None
