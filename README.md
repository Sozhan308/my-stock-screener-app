# My Stock Screener

A proper Python + FastAPI + React/TypeScript application for scanning NSE equities using a configurable version of the Minervini Trend Template.

## Stack

### Backend

- Python 3.12+
- `uv`
- FastAPI
- Pandas / NumPy
- yfinance
- Typer
- Pydantic Settings
- Rich terminal progress UI

### Frontend

- React
- TypeScript
- Vite
- Lucide React

FastAPI is used strictly as the backend/API layer. React is responsible for the browser UI.

## Architecture

```text
                        Browser
                           │
                           ▼
                 ┌───────────────────┐
                 │ React + TypeScript│
                 │      Vite UI      │
                 └─────────┬─────────┘
                           │ REST / JSON
                           ▼
                 ┌───────────────────┐
                 │      FastAPI      │
                 │      Backend      │
                 ├───────────────────┤
                 │ Scanner           │
                 │ Indicators        │
                 │ Minervini Rules   │
                 │ Market Data       │
                 └─────────┬─────────┘
                           │
                           ▼
                    Yahoo Finance
```

## Repository layout

```text
minervini-nse-scanner/
├── pyproject.toml
├── .env.example
├── README.md
├── Dockerfile
├── nse_symbols.example.csv
│
├── src/
│   └── minervini_scanner/
│       ├── api.py
│       ├── cli.py
│       ├── config.py
│       ├── data.py
│       ├── indicators.py
│       ├── models.py
│       ├── rules.py
│       └── scanner.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig*.json
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       └── styles.css
│
├── tests/
└── .github/workflows/ci.yml
```

## Setup

### Backend

```bash
uv sync --extra dev
```

Create `nse_symbols.csv`:

```csv
SYMBOL
RELIANCE
HDFCBANK
ICICIBANK
INFY
TCS
HCLTECH
...
```

### Run a scan

```bash
uv run minervini scan --timeframe daily
```

or:

```bash
uv run minervini scan --timeframe 4h
```

The scan shows live progress while downloading data and evaluating the rules, followed by a scan summary.

The scan writes:

```text
output/minervini_daily.csv
output/minervini_daily.xlsx
```

## Start backend

```bash
uv run minervini api
```

API:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Useful endpoint:

```text
GET /api/stocks?timeframe=daily&min_score=7&min_rs=70
```

## Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Vite proxies `/api` to FastAPI.

## UI features

- Daily / 4H switch
- Minimum score filter
- Minimum RS filter
- Stock search
- 9-rule visual checklist
- 9/9 and 8/9 summary counts
- RS ranking
- MA50 / MA150 / MA200 values
- 200-MA slope
- 52-week high/low distance
- Stock detail modal
- Direct TradingView chart links

## Checklist

1. Price > MA50
2. Price > MA150
3. Price > MA200
4. MA50 > MA150
5. MA150 > MA200
6. MA200 rising
7. Price >=25% above 52-week low
8. Price <=25% below 52-week high
9. Universe-relative RS rating >= threshold

The current RS rating is a project-defined percentile ranking, not the proprietary IBD RS Rating.

## Development

Backend:

```bash
uv run ruff check .
uv run pytest
```

Frontend:

```bash
cd frontend
npm run build
```

## Data

The initial implementation uses Yahoo Finance through `yfinance`. Market-data availability, corporate actions, gaps, and intraday history limitations should be validated against the charting/data source you ultimately intend to use.

This project is for research and screening, not investment advice.
