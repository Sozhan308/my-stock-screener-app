# Running the app

Step-by-step instructions for setting up and running the scanner and dashboard on your own machine (macOS / Linux).

## 1. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.12+ (uv installs it if missing) | `uv run python --version` |
| [uv](https://docs.astral.sh/uv/) | recent | `uv --version` |
| Node.js | 20.19+ or 22.12+ (required by Vite 7) | `node --version` |
| npm | comes with Node.js | `npm --version` |
| git | any | `git --version` |

## 2. First-time setup

```bash
git clone https://github.com/Sozhan308/my-stock-screener-app.git
cd my-stock-screener-app

uv sync --dev                 # Python dependencies (creates .venv)
cd frontend && npm install    # dashboard dependencies
cd ..
```

The repository already contains:

- `nse_symbols.csv` — the scan universe (~750 NSE symbols). Edit it to change the universe. (`nse_symbols.example.csv` is a 23-symbol list that is handy for a quick test: `uv run minervini scan --symbols-file nse_symbols.example.csv`.)
- `output/minervini_daily.csv` and `output/minervini_4h.csv` — the latest results from the nightly GitHub Actions scan, so the dashboard works without running a scan locally.
- `data/fno_lots.csv` — F&O lot sizes.
- `data/watchlist.db` — your watchlist.

## 3. Start the dashboard

Use two terminals, both in the repository folder.

**Terminal 1 — backend (FastAPI):**

```bash
uv run minervini api
```

It serves on <http://127.0.0.1:8000> and reloads automatically when Python files change. Check it with `curl http://127.0.0.1:8000/api/health` → `{"status":"ok"}`.

**Terminal 2 — frontend (Vite + React):**

```bash
cd frontend
npm run dev
```

Open **<http://localhost:5173>** in the browser. (On macOS Vite listens on `localhost`, which may resolve to IPv6; use `localhost` rather than `127.0.0.1`.) The frontend forwards `/api` requests to the backend on port 8000, so both terminals must stay open.

Stop either one with `Ctrl+C`.

## 4. Everyday routine

The nightly GitHub Actions job (weekdays, 18:00 IST) refreshes the data, commits new results and sends the Telegram digest. To see the latest results locally:

```bash
git pull                      # new scan results, F&O list, code changes
uv sync                       # only needed when Python dependencies changed
(cd frontend && npm install)  # only needed when frontend dependencies changed
```

Then start the backend and frontend as in step 3. If they are already running, click **Refresh** in the dashboard after pulling — the backend reads the CSV files on every request.

See the [user guide](user-guide.md) for how to read the screen, the chart and the digest.

## 5. Running the scans yourself (optional)

You do not need this if you rely on the nightly job, but it is useful for intraday checks or after changing the universe.

```bash
make update                   # Daily + 4H scans (same as: uv run minervini update)
make scan-daily               # Daily only
make scan-4h                  # 4H only
```

- **First run:** downloads ~5 years of daily and ~2 years of hourly bars for every symbol into `data/cache/` (git-ignored, ~180 MB for ~750 symbols). Takes about 2–3 minutes.
- **Later runs:** only the last few days are downloaded; a full Daily + 4H update takes about a minute.
- Results are written to `output/`. These files are also updated by the nightly job, so if you run scans locally, discard your local `output/` changes before pulling (`git checkout -- output/`) to avoid merge conflicts. To keep local scans separate, write them elsewhere and point the API at that folder:

```bash
MINERVINI_OUTPUT_DIR=/tmp/scan-out uv run minervini update
MINERVINI_OUTPUT_DIR=/tmp/scan-out uv run minervini api
```

Charts do not need a local scan: the first time you open a chart for a symbol, the backend downloads that symbol's history (about a second) and caches it.

## 6. Other commands

| Command | What it does |
|---|---|
| `uv run minervini notify --dry-run` | Print the Telegram digest built from the current `output/` CSVs |
| `TELEGRAM_BOT_TOKEN=… TELEGRAM_CHAT_ID=… uv run minervini notify` | Send the digest from your machine |
| `uv run minervini journal-check trades.csv` | Replay the setup detector on past `symbol,date` rows (keep personal journals outside the repo) |
| `uv run minervini update-fno` | Refresh `data/fno_lots.csv` from NSE |
| `make check` | Lint, format check and tests (what CI runs) |
| `make fix` | Auto-fix lint/format issues, then run tests |
| `cd frontend && npm run build` | Type-check and build the dashboard |

## 7. Configuration

Settings can be overridden with environment variables (prefix `MINERVINI_`) or a `.env` file in the repository root:

```dotenv
MINERVINI_OUTPUT_DIR=output
MINERVINI_DATA_DIR=data/cache
MINERVINI_MIN_SCORE=7
MINERVINI_RS_THRESHOLD=70        # the 9th trend-template rule (the dashboard RS filter is separate)
MINERVINI_MIN_TRADED_VALUE_CR=5
MINERVINI_MIN_PRICE=30
MINERVINI_REQUEST_DELAY=0.5      # pause between Yahoo download batches (seconds)
```

`.env` is git-ignored. Never put the Telegram token in it if you might share the folder; use the GitHub secrets for the nightly job.

## 8. GitHub Actions setup (one-time)

1. Repository secrets for the Telegram digest:
   ```bash
   gh secret set TELEGRAM_BOT_TOKEN      # paste the token when prompted
   gh secret set TELEGRAM_CHAT_ID --body <your chat id>
   ```
2. Run the scan on demand: **GitHub → Actions → Stock Market Scan → Run workflow**. Otherwise it runs on weekdays at 18:00 IST.

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `http://127.0.0.1:5173` does not load | Use `http://localhost:5173` |
| Dashboard shows "No stocks match the current filters" | Run `git pull` (or `make update`); relax filters or switch to *All stocks* |
| Everything shows 0 although `data/cache/` is full | The dashboard reads the scan results in `output/*.csv`, **not** the cache. The cache is only the raw price history the scanner reads. If the CSVs are missing or were made by an older version (no `Stage`/`Setup` columns), run `make update` (about a minute with a warm cache), then click **Refresh** |
| Dashboard loads but data never appears | The backend is not running — start `uv run minervini api` |
| `Address already in use` (port 8000 or 5173) | Another instance is running; stop it (`lsof -i :8000` to find the PID, then `kill <PID>`), or use `uv run minervini api --port 8001` and update `frontend/vite.config.ts` |
| Chart says "No price data" | No network on first load for that symbol, or the symbol is unknown to Yahoo |
| `npm run dev` fails with an engine/version error | Upgrade Node.js to 20.19+ or 22.12+ |
| `git pull` conflicts in `output/` | `git checkout -- output/` then pull again (the nightly results replace local ones) |
