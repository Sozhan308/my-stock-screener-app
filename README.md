# My Stock Screener

A Python + FastAPI + React/TypeScript application for screening NSE
equities using a configurable implementation of the Minervini Trend
Template.

> This project is for research and screening purposes only. It is not
> investment advice.

## Features

### Stock Screening

-   NSE equity universe
-   Daily and 4H timeframes
-   Configurable minimum checklist score
-   Configurable minimum RS rating
-   Minervini Trend Template checklist
-   Universe-relative RS percentile
-   Moving-average analysis
-   52-week high/low analysis
-   Rich terminal progress reporting
-   CSV and Excel output

### Web UI

-   React + TypeScript + Vite
-   Daily / 4H switching
-   Minimum score and RS filtering
-   Stock search
-   9-rule visual checklist
-   Candidate detail view
-   Persistent browser watchlist
-   TradingView chart links
-   MA50 / MA150 / MA200 values
-   200-MA slope
-   52-week high/low distance
-   Interactive filtering through FastAPI

### Automation

-   GitHub Actions CI
-   Ruff linting and formatting checks
-   Pytest
-   Automated daily market-data refresh
-   Daily + 4H scan
-   Automatic scan-result commits
-   Manual workflow execution

## Architecture

``` text
                              GitHub
                                 │
                  ┌──────────────┴──────────────┐
                  │                             │
                  ▼                             ▼
          GitHub Actions CI             Daily Scan Pipeline
                  │                             │
          Ruff + Pytest                  Yahoo Finance
                  │                             │
                  │                     Daily + 4H scan
                  │                             │
                  │                             ▼
                  │                    output/*.csv
                  │                    output/*.xlsx
                  │                             │
                  │                             ▼
                  │                       Git commit
                  │
                  ▼
              GitHub Repository
                  │
          ┌───────┴────────┐
          ▼                ▼
       FastAPI          React/Vite
       Backend          Frontend
          │                │
          └──── REST/JSON ─┘
```

FastAPI is strictly the backend/API layer. React is responsible for the
browser UI.

## Technology Stack

### Backend

-   Python 3.12+
-   `uv`
-   FastAPI
-   Pandas / NumPy
-   yfinance
-   Typer
-   Pydantic Settings
-   Rich
-   OpenPyXL
-   Uvicorn

### Development

-   Ruff
-   Pytest
-   Pytest-Cov
-   HTTPX
-   Make

### Frontend

-   React
-   TypeScript
-   Vite
-   Lucide React

### Automation

-   GitHub Actions
-   GitHub Actions Bot
-   Yahoo Finance via `yfinance`

## Repository Structure

``` text
my-stock-screener-app/
├── pyproject.toml
├── uv.lock
├── Makefile
├── README.md
├── .gitignore
├── .env.example
├── Dockerfile
├── nse_symbols.example.csv
│
├── src/
│   └── minervini_scanner/
│       ├── __init__.py
│       ├── api.py
│       ├── cli.py
│       ├── config.py
│       ├── data.py
│       ├── indicators.py
│       ├── models.py
│       ├── progress.py
│       ├── rules.py
│       └── scanner.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       └── styles.css
│
├── tests/
│
├── output/
│   ├── minervini_daily.csv
│   ├── minervini_daily.xlsx
│   ├── minervini_4h.csv
│   └── minervini_4h.xlsx
│
└── .github/
    └── workflows/
        ├── ci.yml
        └── daily-scan.yml
```

## Setup

### Prerequisites

-   Python 3.12+
-   `uv`
-   Node.js 20+
-   npm

### Backend

``` bash
uv sync --dev
```

Development dependencies include Ruff, Pytest, Pytest-Cov, and HTTPX.

## NSE Symbol Universe

The scanner reads the NSE symbol universe from:

``` text
nse_symbols.csv
```

Example:

``` csv
SYMBOL
RELIANCE
HDFCBANK
ICICIBANK
INFY
TCS
HCLTECH
```

A template is provided as `nse_symbols.example.csv`.

``` bash
cp nse_symbols.example.csv nse_symbols.csv
```

## Running the Scanner

### Daily

``` bash
uv run minervini scan --timeframe daily
```

### 4H

``` bash
uv run minervini scan --timeframe 4h
```

The scanner displays live progress while downloading market data and
evaluating the rules.

Example:

``` text
──────────────────── MINERVINI NSE SCANNER ────────────────────
  Timeframe: DAILY
  Universe: 500 symbols

  Downloading market data ━━━━━━━━━━━━━━━━━━━━ 500/500

──────────────── APPLYING MINERVINI RULES ────────────────────
  Applying Minervini rules ━━━━━━━━━━━━━━━━━━━ 484/484

────────────────────── SCAN COMPLETE ─────────────────────────
  Stocks scanned       : 500
  Valid results        : 484
  Skipped / invalid    : 16
  9/9 candidates       : 88
  8/9 candidates       : 52
  7/9 candidates       : 42
  Shortlisted (>=7/9)  : 182
```

## Candidate Threshold

The current default candidate threshold is:

``` text
Score >= 7/9
```

The scanner treats 9/9, 8/9, and 7/9 as qualifying candidates:

``` text
9/9 → qualifies
8/9 → qualifies
7/9 → qualifies
<7/9 → excluded
```

The score remains visible so the individual checklist results can be
inspected.

## Minervini Checklist

The current implementation evaluates nine conditions:

1.  Price \> MA50
2.  Price \> MA150
3.  Price \> MA200
4.  MA50 \> MA150
5.  MA150 \> MA200
6.  MA200 rising
7.  Price \>=25% above 52-week low
8.  Price \<=25% below 52-week high
9.  Universe-relative RS rating \>= threshold

A stock qualifies as a candidate when it satisfies at least 7/9.

### RS Rating

The current RS rating is a project-defined universe-relative percentile
ranking. It is **not** the proprietary IBD RS Rating.

## Scan Output

The scanner generates:

``` text
output/
├── minervini_daily.csv
├── minervini_daily.xlsx
├── minervini_4h.csv
└── minervini_4h.xlsx
```

The CSV files are consumed by the FastAPI backend. Excel files are
useful for manual analysis.

## FastAPI Backend

Start the backend:

``` bash
uv run minervini api
```

API:

``` text
http://127.0.0.1:8000
```

Swagger:

``` text
http://127.0.0.1:8000/docs
```

### API Examples

``` text
GET /api/stocks?timeframe=daily&min_score=7&min_rs=70
GET /api/stocks?timeframe=4h&min_score=7&min_rs=70
GET /api/stocks/HCLTECH?timeframe=daily
```

The API allows the frontend to change screening parameters without
rerunning Yahoo Finance downloads. For example, `RS >= 70` can be
changed dynamically to `RS >= 60` against the existing scan dataset.

## React Frontend

``` bash
cd frontend
npm install
npm run dev
```

Open:

``` text
http://127.0.0.1:5173
```

Vite proxies `/api` requests to FastAPI.

## UI

### Filters

-   Daily / 4H
-   Minimum score
-   Minimum RS rating
-   Stock search

### Candidate statistics

-   Total shortlisted
-   9/9 count
-   8/9 count
-   7/9 count
-   Average RS

### Candidate table

-   Symbol
-   Score
-   RS rating
-   Price
-   MA50
-   MA150
-   MA200
-   200-MA slope
-   Distance from 52-week low
-   Distance from 52-week high
-   Checklist
-   TradingView link

### Candidate details

Clicking a stock opens a detailed view containing the full checklist,
moving averages, 200-MA slope, 52-week range, RS rating, and TradingView
link.

### Watchlist

Candidates can be added to a local browser watchlist. The watchlist is
stored using browser local storage and survives page refreshes.

## Makefile

Common development commands are available through `make`:

``` bash
make install
make lint
make format
make format-check
make test
make check
make scan-daily
make scan-4h
make update
```

The recommended local pre-push check is:

``` bash
make check
```

## Code Quality

``` bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Format automatically:

``` bash
uv run ruff format .
```

Or run all checks:

``` bash
make check
```

## Continuous Integration

GitHub Actions runs CI on pushes and pull requests.

Workflow:

``` text
.github/workflows/ci.yml
```

Pipeline:

``` text
Checkout
   ↓
Install uv
   ↓
Install Python 3.12
   ↓
uv sync --dev
   ↓
Ruff lint
   ↓
Ruff format check
   ↓
Pytest
```

## Automated Daily Market Scan

Workflow:

``` text
.github/workflows/daily-scan.yml
```

The workflow runs every evening at approximately 18:00 IST. GitHub
Actions cron uses UTC, so the configured schedule is 12:30 UTC.

It can also be triggered manually from:

``` text
GitHub → Actions → Daily Market Scan → Run workflow
```

### Daily Scan Pipeline

``` text
Scheduled GitHub Action
          │
          ▼
    Checkout repository
          │
          ▼
       Install uv
          │
          ▼
      Python 3.12
          │
          ▼
       uv sync
          │
          ▼
uv run minervini update
          │
          ├───────────────┐
          ▼               ▼
      Daily scan        4H scan
          │               │
          └───────┬───────┘
                  ▼
          Generate outputs
                  │
          ├── minervini_daily.csv
          ├── minervini_daily.xlsx
          ├── minervini_4h.csv
          └── minervini_4h.xlsx
                  │
                  ▼
           Validate outputs
                  │
                  ▼
          Commit changes
                  │
                  ▼
             Push to main
```

Automated commits use the standard `github-actions[bot]` identity.

Example:

``` text
chore: update daily market scan
```

## Data Refresh Strategy

``` text
Yahoo Finance
      ↓
yfinance
      ↓
Market data
      ↓
Indicators
      ↓
Minervini rules
      ↓
Scan dataset
```

The automated pipeline refreshes the candidate dataset daily. The
frontend does not download market data itself.

## Interactive Filtering vs Data Refresh

### Data refresh

Runs periodically:

``` text
Yahoo Finance
      ↓
Market data
      ↓
Indicators
      ↓
Minervini rules
      ↓
Scan dataset
```

### Interactive filtering

Runs whenever the user changes filters:

``` text
React UI
   ↓
FastAPI
   ↓
Existing scan dataset
   ↓
Filtered results
```

This means filters such as minimum RS can be changed without downloading
market data again.

## Development Workflow

Typical local development:

``` bash
uv sync --dev

make check

make scan-daily
make scan-4h

uv run minervini api
```

In another terminal:

``` bash
cd frontend
npm install
npm run dev
```

Before pushing code:

``` bash
make check
git status
git add .
git commit -m "your commit message"
git push
```

## Future Roadmap

-   Automated setup detection
-   Consolidation detection
-   Breakout proximity
-   Pullback detection
-   Volume analysis
-   Volatility contraction analysis
-   Candidate ranking
-   More configurable technical filters
-   Persistent server-side watchlists
-   Public deployment
-   FastAPI production deployment
-   React production deployment
-   Better market-data caching
-   Additional screening strategies

Intended workflow:

``` text
NSE Universe
     ↓
Minervini 7/9+
     ↓
Candidate Watchlist
     ↓
Setup Detection
     ↓
Manual TradingView Analysis
     ↓
Trading Decision
```

The scanner identifies research candidates. It does not automatically
generate buy or sell decisions.

## Data Limitations

The initial implementation uses Yahoo Finance through `yfinance`.

Market-data availability, corporate actions, missing candles, ticker
changes, intraday history limitations, and data-provider differences
should be validated against the charting/data source ultimately used for
trading decisions.

The 4H timeframe is generated from available intraday data and should be
independently validated against corresponding TradingView charts.

## Disclaimer

This software is a personal research and screening tool.

It does not provide investment, financial, or trading advice.

Always independently verify prices, technical conditions, corporate
actions, and market data before making any investment or trading
decision.
