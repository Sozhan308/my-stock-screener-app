# My Stock Screener

A Python + FastAPI + React/TypeScript application for screening NSE equities using a configurable implementation of the Minervini Trend Template.

The scanner analyzes Daily and 4H market data and identifies stocks that satisfy the configured technical criteria.

> This project is for research and screening purposes only. It is not investment advice.

## Features

- NSE equity screening
- Daily and 4H timeframes
- Minervini Trend Template checklist
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
- Automated daily market-data refresh
- GitHub Actions CI

## Tech Stack

### Backend

- Python 3.12+
- FastAPI
- Pandas / NumPy
- yfinance
- Typer
- Rich

### Frontend

- React
- TypeScript
- Vite
- Lucide React

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
- Node.js 20+
- npm

### Install

Clone the repository and install the Python dependencies:

```bash
uv sync --dev
```

Create the NSE symbol list:

```bash
cp nse_symbols.example.csv nse_symbols.csv
```

Edit `nse_symbols.csv` if you want to customize the screening universe.

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
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
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

The RS rating is a project-defined universe-relative percentile and is **not** the proprietary IBD RS Rating.

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
- Automatic update of scan results

The automated market scan runs in the evening and commits updated results to the repository.

## Data

Market data is currently sourced from Yahoo Finance through `yfinance`.

Data availability, corporate actions, missing candles, and intraday-history limitations should be independently validated against the charting/data source used for actual trading decisions.

The 4H results should also be validated against the corresponding TradingView charts.

## Disclaimer

This software is a personal research and screening tool.

It does not provide investment, financial, or trading advice.

Always independently verify market data and technical conditions before making any investment or trading decision.
