# Roadmap

## Done

| Area | Delivered |
|---|---|
| Data | Parquet OHLCV cache, incremental batched downloads, re-adjustment detection, hourly fallback for recent listings, late daily bars rebuilt from hourly |
| Detection | Daily VCP, Daily Power play, 4H VCP, 1H power play hint; shakeouts; pivot/stop/risk; entry zone; stages; setup score |
| Dashboard | Actionable / all setups / all stocks views, setup columns, setup-score and liquidity filters, F&O / 1H / SO tags, annotated chart, watchlist that ignores filters, RS default 60 |
| Alerts | Telegram digest from the nightly GitHub Actions job |
| Tooling | `journal-check`, `update-fno`, `notify`, tests for detector, store, API, digest and F&O parsing |

## Next

1. **Market regime gauge** — breadth (% of the universe above the 50/200-day averages), new highs vs new lows, Nifty trend, and the follow-through rate of recent breakouts, shown as *Healthy / Caution / Defensive* on the dashboard and in the digest. Historical entries showed that breakout success depends strongly on market conditions.
2. **Scan history** — store each scan run (and backfill from the git history of `output/*.csv`) to show "new today", days in base and stage changes.
3. **Review queue** — keyboard-driven review (next / previous / star / reject with reason), mini-chart grid, and remembering rejected setups until their stage changes.
4. **Trade-plan watchlist** — per-stock pivot, stop, risk, notes, status (watching / triggered / invalidated / bought) and performance since added; Telegram alerts on pivot breaks and stop hits.
5. **Exit / hold alerts** — rules from the trading journal: close below the 20 EMA (Daily/4H) on high volume, no follow-through within two bars, extension far above the pivot.

## Later

- **Sector / industry strength** — group RS ranking and a column/filter.
- **Backtesting** — walk-forward detection on history; forward returns, win rate and adverse excursion; tune presets and score weights.
- **Learning from reviews** — use star/reject decisions as labels to rank setups.

## Small fixes still open

- TradingView link opens the symbol page instead of the chart.
- 4H "MA200 rising" looks back 33 bars (~16 trading days) instead of 22 trading days.
- Daily XLSX exports are committed every night (repository growth).
- `jinja2` dependency is unused.
- Trend-template thresholds shown in the dashboard should come from the backend settings.
