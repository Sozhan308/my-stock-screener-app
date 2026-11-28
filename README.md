# My Stock Screener

A Python + FastAPI + React/TypeScript application for screening NSE equities using a configurable implementation of the Minervini Trend Template, plus automatic detection of rally → contraction (VCP / Power play) → breakout setups.

The scanner analyzes Daily and 4H market data, identifies stocks that satisfy the trend criteria, and classifies each stock's setup stage (Forming, Ready, Breakout, ...) with a pivot, stop and setup score so that only actionable charts need a manual review.

> This project is for research and screening purposes only. It is not investment advice.

📚 **Documentation:** [running the app](docs/running-the-app.md) · [user guide](docs/user-guide.md) · [setup detection](docs/setup-detection.md) · [architecture](docs/architecture.md) · [decisions](docs/decisions.md) · [roadmap](docs/roadmap.md)

## Features

- NSE equity screening
- Daily and 4H timeframes
- Minervini Trend Template checklist
- VCP and Power play setup detection with pivot, stop, risk and setup score
- Shakeout (undercut and reclaim) detection
- 1H power-play hint
- Annotated in-app chart (base, contractions, pivot, stop, breakout)
- F&O tag with lot size
- Liquidity flag (average traded value and price)
- Configurable minimum score
- Relative Strength (RS) ranking
- Moving-average analysis
- 52-week high/low analysis
- Interactive React dashboard
- Stock search and filtering
- Candidate details and checklist
- Personal watchlist
- TradingView chart links
- CSV and Excel exports
- Local OHLCV cache with incremental, batched downloads
- Journal check: replay the detector on past trade dates
- Telegram evening digest
- Automated daily market-data refresh
- GitHub Actions CI

## Tech Stack

### Backend

- Python 3.12+
- FastAPI
- Pandas / NumPy
- yfinance
- PyArrow (Parquet cache)
- Typer
- Rich

### Frontend

- React
- TypeScript
- Vite
- Lucide React
- TradingView Lightweight Charts

### Development & Tooling

- uv
- Ruff
- Pytest
- Make
- GitHub Actions

## Quick Start

### Prerequisites

- Python 3.12+
- uv
- Node.js 20.19+ or 22.12+
- npm

### Install

Clone the repository and install the dependencies:

```bash
uv sync --dev
cd frontend && npm install
```

The repository already includes `nse_symbols.csv` (every NSE EQ-series stock, ~2,400, refreshed nightly with `uv run minervini update-universe`); edit it only for a custom universe. `nse_symbols.example.csv` is a small list for quick tests (`--symbols-file nse_symbols.example.csv`).

See [docs/running-the-app.md](docs/running-the-app.md) for the full step-by-step guide.

## Run the Scanner

### Daily

```bash
uv run minervini scan --timeframe daily
```

### 4H

```bash
uv run minervini scan --timeframe 4h
```

The scanner displays progress while downloading market data and evaluating the screening rules.

Daily and hourly bars are cached as Parquet files under `data/cache/` (git-ignored). The first run downloads the full history (5 years daily, ~2 years hourly); later runs only download the last few days in batches. If Yahoo re-adjusts history (splits, dividends), the affected symbol is re-downloaded automatically.

Results are written to:

```text
output/
├── minervini_daily.csv
├── minervini_daily.xlsx
├── minervini_4h.csv
└── minervini_4h.xlsx
```

## Run the Web Application

Start the FastAPI backend:

```bash
uv run minervini api
```

Then start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

The React frontend communicates with the FastAPI backend and allows filters such as minimum score and RS rating to be changed without rerunning the market-data download.

## Minervini Checklist

The scanner currently evaluates 9 conditions:

1. Price > MA50
2. Price > MA150
3. Price > MA200
4. MA50 > MA150
5. MA150 > MA200
6. MA200 rising
7. Price >= 25% above 52-week low
8. Price <= 25% below 52-week high
9. Universe-relative RS rating >= threshold

The default candidate threshold is:

```text
7 / 9
```

Therefore, stocks scoring 7/9, 8/9, or 9/9 are shortlisted.

The RS rating is a project-defined percentile within the liquid universe (50-day average traded value ≥ ₹5 Cr, price ≥ ₹30) and is **not** the proprietary IBD RS Rating.

## Setup Detection

Every stock is also checked for a rally → contraction → breakout setup, with timeframe-specific presets (Daily VCP, Daily Power play, 4H VCP and a 1H power-play hint). Each stock gets a stage (Breakout, Ready, Recent breakout, Forming, Extended, Failed, No base), a pivot, a stop, a risk %, the contraction depths, shakeouts and a 0–100 setup score. The dashboard defaults to *Actionable setups* ranked by stage and setup score, and the stock popup shows an annotated chart of the base.

See [docs/setup-detection.md](docs/setup-detection.md) for the algorithm, presets, stages, scoring and validation, and [docs/user-guide.md](docs/user-guide.md) for how to use it.

To check the detector against your own past trades (CSV with `symbol` and `date` columns; keep personal journals out of the repository):

```bash
uv run minervini journal-check trades.csv
```

## Telegram Digest

After the nightly scan, GitHub Actions sends a digest (breakouts, top Ready setups, 4H setups, watchlist alerts) to Telegram when the repository secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set. Preview it locally with:

```bash
uv run minervini notify --dry-run
```

## Development

Install development dependencies:

```bash
make install
```

Run all checks:

```bash
make check
```

Automatically fix lint and formatting issues:

```bash
make fix
```

Run tests:

```bash
make test
```

Run individual scans:

```bash
make scan-daily
make scan-4h
```

Run the complete Daily + 4H update:

```bash
make update
```

## Automation

GitHub Actions provides:

- Continuous integration on code changes
- Ruff linting and formatting checks
- Automated tests
- Daily market-data refresh
- Daily + 4H scan generation
- Automatic update of scan results and the F&O lot-size list
- Telegram digest
- Market-data cache between runs (`actions/cache`)

The automated market scan runs on weekday evenings (18:00 IST) and commits updated results to the repository.

## Data

Market data is currently sourced from Yahoo Finance through `yfinance`.

Data availability, corporate actions, missing candles, and intraday-history limitations should be independently validated against the charting/data source used for actual trading decisions.

The 4H results should also be validated against the corresponding TradingView charts.

## Disclaimer

This software is a personal research and screening tool.

It does not provide investment, financial, or trading advice.

Always independently verify market data and technical conditions before making any investment or trading decision.
