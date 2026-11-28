from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_dir: Path = Path("data/cache")
    output_dir: Path = Path("output")
    watchlist_db: Path = Path("data/watchlist.db")
    fno_file: Path = Path("data/fno_lots.csv")
    default_timeframe: str = "daily"
    rs_threshold: float = 70.0
    min_score: int = 7
    # Pause between batched Yahoo Finance requests (seconds).
    request_delay: float = 0.5
    min_traded_value_cr: float = 5.0
    min_price: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MINERVINI_",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.watchlist_db.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
