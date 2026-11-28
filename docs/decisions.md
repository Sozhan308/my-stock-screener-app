# Decision log

Each entry records the context, the decision and its consequences. Newest decisions first within a date.

## 2026-11-28

### D1 — Detect the setup automatically instead of reviewing every trend-template chart
- **Context:** About 190 stocks pass the trend-template filter on a typical day; each had to be opened to check for a rally, a compression with two or three swings, and a breakout.
- **Decision:** Add a detector (`setups.py`) that finds the base, measures the contractions, marks pivot and stop, assigns a stage and a 0–100 setup score. The dashboard defaults to *Actionable setups* (Breakout, Ready, Recent breakout).
- **Consequences:** The review list drops to roughly 30–70 ranked stocks per day. Thresholds live in code presets and are documented in [setup detection](setup-detection.md).

### D2 — Bar-based presets for several timeframes and setup types
- **Context:** A review of historical entries showed three kinds of setups: multi-week Daily bases, 4–10 day bases visible on 4H, and 1–6 day pauses after a sharp run ("power play"). The original spec (base 3 weeks – 12 months) only covered the first kind.
- **Decision:** One timeframe-agnostic algorithm with presets: Daily VCP (user spec: ≥ 25% rally within 3 months, base 3 weeks – 12 months, ≤ 20% deep), Daily Power play, 4H VCP, and a 1H power play shown as a hint only.
- **Consequences:** 19 of 24 historical entries flagged on Daily/4H, 21 of 24 when the 1H hint is checked through the entry day.

### D3 — VCP rule: tighten from the deepest contraction, 10% tolerance, shakeouts allowed
- **Context:** The initial choice was a strict VCP (every pullback shallower than the previous one, rising lows). Real bases were rarely strictly shrinking (e.g. 5.7% → 7.9% → 6.9%), and shakeouts make the last leg deeper by design.
- **Decision:** Evaluate contractions from the deepest one onwards; each may be up to 1.1× the previous; a low that undercuts the previous low by ≤ 3% and is reclaimed within 3 bars is a shakeout and is exempt.
- **Consequences:** Recall on historical entries rose from 7/24 to 19/24 while messy bases are still rejected.

### D4 — Breakout = close above pivot; volume is a warning, not a filter
- **Context:** Preferred confirmation is a close above the pivot on ≥ 1.5× average volume, but many valid breakouts are only discovered at the evening close and some confirm volume the next day.
- **Decision:** A close above the pivot sets the stage to *Breakout*; volume below 1.5× adds the ⚠ note and lowers the setup score (5 instead of 15 points).
- **Consequences:** Low-volume breakouts stay visible but rank below confirmed ones.

### D5 — Pivot, stop and entry zone definitions
- **Decision:** Pivot = most recent confirmed swing high in the base; stop = lowest low since that pivot; entry zone = third of the base range the pivot sits in (Low cheat / Cheat / Handle). *Ready* requires the close to be at or below the pivot (within 5% on Daily, 3% on 4H / power play, 1.5% on 1H).
- **Consequences:** Matches the entry vocabulary used in the trading journal; detected pivots were within ~0.5% of hand-drawn levels in 9 historical cases.

### D6 — RS filter default lowered to 60; trend-template RS rule stays at 70
- **Context:** The RS ≥ 70 filter alone would have hidden 4 of 24 historical entries.
- **Decision:** Dashboard and API default `min_rs` = 60; the ninth trend-template rule (`RS > threshold`) keeps 70, so a 9/9 score keeps its meaning.

### D7 — Liquidity rule
- **Decision:** *Liquid* = 50-day average traded value ≥ ₹5 Cr and price ≥ ₹30. Shown as a column and a *Liquid only* toggle (on by default in the dashboard and the digest).

### D8 — Local OHLCV cache with incremental, batched downloads
- **Context:** Sequential per-symbol downloads took several minutes and re-downloaded the same data for each scan.
- **Decision:** Parquet cache per symbol/interval under `data/cache/` (git-ignored), batched incremental Yahoo downloads, automatic full re-download when history was re-adjusted, `actions/cache` between nightly runs.
- **Consequences:** Full Daily + 4H update in about one minute. Enables replaying past dates (`journal-check`) and future backtesting.

### D9 — Rebuild late daily bars from hourly bars
- **Context:** Yahoo often publishes the latest NSE daily bar late (prices empty, volume present), which made the evening scan a day behind for most stocks.
- **Decision:** At analysis time, sessions present in hourly bars but missing from daily bars are rebuilt from hourly bars; volume is scaled by the stock's own hourly/daily volume ratio (hourly bars capture ~75% of daily volume). The cache itself is not modified.

### D10 — F&O as a tag, not a filter
- **Decision:** Keep a snapshot of NSE's lot-size file in `data/fno_lots.csv`, refresh it nightly on a best-effort basis (`minervini update-fno`), and show an **F&O** tag next to the symbol with the lot size on hover. No filter.

### D11 — 1H power play as a hint only
- **Context:** Short intraday pauses can be caught on 1H, but they are hard to act on during working hours.
- **Decision:** Compute it in both scans and show it as a purple **1H** tag and in the digest; it does not change the stage, ranking or filters.

### D12 — Annotated chart inside the app
- **Decision:** Use TradingView Lightweight Charts (Apache-2.0) in the stock popup with base lines, contraction zig-zag and depths, pivot/stop lines and shakeout/breakout markers. The chart endpoint recomputes the setup from the latest cached bars.

### D13 — Telegram digest from GitHub Actions
- **Decision:** After the nightly scan, `minervini notify` sends breakouts, top Ready setups, 4H setups and watchlist alerts to Telegram. Credentials live only in repository secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`); no server is needed. The step is best-effort so a Telegram outage never fails the scan.

### D14 — Watchlist view ignores filters
- **Context:** The watchlist view only filtered the already-filtered table, so saved stocks vanished when they dropped below a filter.
- **Decision:** The watchlist view requests all stocks and shows every saved symbol with its current stage.

### D15 — Personal trading data stays out of the repository
- **Context:** The repository is public.
- **Decision:** Journals, P/L and personal identifiers are never committed. `journal-check` reads a local CSV supplied by the user. Documentation reports only aggregate detection results.

### D16 — Nightly scan on weekdays only
- **Decision:** Cron `30 12 * * 1-5` (18:00 IST, Monday–Friday).

## Earlier decisions (before 2026-11-28)

- Python + FastAPI backend, React + TypeScript (Vite) frontend, `uv`, Ruff, pytest, GitHub Actions.
- Yahoo Finance (`yfinance`) as the market-data source.
- Minervini trend template with 9 rules; candidate threshold 7/9; RS is a universe-relative percentile of weighted 3/6/9/12-month returns (not the IBD rating).
- Daily and 4H scans; 4H candles resampled from hourly bars.
- Watchlist stored server-side in SQLite and committed to the repository.
