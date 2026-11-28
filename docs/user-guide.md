# User guide

This platform narrows the NSE universe down to the stocks that show the setup this project is built around:

> **A strong rally → a compression of a few days to a few months with two or three tightening swings → a breakout above the pivot.**

Instead of opening every trend-template stock to check for a compression by eye, the scanner finds the base, measures each pullback, marks the pivot and stop, and ranks the stocks by how close and how clean the setup is. You review a short, ranked list and the annotated chart, then decide.

## 1. The daily routine

| When | What happens | What you do |
|---|---|---|
| Weekdays ~18:00 IST | GitHub Actions refreshes market data, runs the Daily and 4H scans, commits the results and sends the Telegram digest | Read the digest on your phone |
| Evening | — | `git pull`, start the app, open **Actionable setups**, review the charts, star the ones you like |
| Next session | — | Watch starred names around the pivot; time the entry on 4H / 1H |

### Starting the app locally

```bash
git pull                      # latest scan results (output/*.csv) and F&O list
uv run minervini api          # terminal 1: backend on http://127.0.0.1:8000
cd frontend && npm run dev    # terminal 2: dashboard on http://localhost:5173
```

See [Running the app](running-the-app.md) for first-time setup, running scans locally, configuration and troubleshooting.

## 2. The dashboard

### Controls

| Control | Meaning | Default |
|---|---|---|
| **Daily / 4H** | Which candle timeframe the table is based on | Daily |
| **Actionable setups / All setups / All stocks** | *Actionable* = Breakout, Ready, Recent breakout. *All setups* adds Forming, Extended and Failed. *All stocks* shows everything that passes the other filters | Actionable setups |
| **Minimum score** | Minimum Minervini trend-template score (0–9) | 7/9 |
| **RS ≥** | Minimum RS rating (percentile among liquid stocks) | 60 |
| **Setup score ≥** | Minimum setup score (0–100) | 0 |
| **Liquid only** | 50-day average traded value ≥ ₹5 Cr and price ≥ ₹30 | On |
| **Search** | Filter by symbol (press Enter) | — |
| **Watchlist** | Show only starred stocks, *ignoring all other filters*, so a starred stock never disappears | Off |

### Summary cards

Count of stocks in the current view, and how many are **Breakout today**, **Ready** and **Recent breakout**.

### Table columns

| Column | Meaning |
|---|---|
| **Stock** | Symbol, watchlist star, and the **F&O** tag if the stock has NSE derivatives (hover for lot size) |
| **Stage** | Setup stage (see below). ⚠ = breakout volume below 1.5× the 50-bar average. A purple **1H** tag means the 1H power play is ready or breaking out |
| **Setup** | `VCP` or `Power play`, plus where the pivot sits in the base: *Low cheat* (lower third), *Cheat* (middle third), *Handle* (upper third) |
| **Setup score** | 0–100 quality score (green ≥ 80, amber ≥ 60) |
| **Pivot** | The breakout level: the most recent confirmed swing high in the base |
| **From pivot** | Distance of the close from the pivot (negative = below) |
| **Stop** | Lowest low since the pivot high (low of the last contraction) |
| **Risk** | Pivot-to-stop distance in % — your risk if you buy at the pivot |
| **Pullbacks %** | Depth of each contraction in the base, oldest first. **SO** = a shakeout in the tightening part of the base |
| **Base** | Base length in bars and its depth from the left-side high |
| **Trend** | Trend-template score (x/9) |
| **RS** | RS rating: percentile among liquid stocks (not the IBD rating; values differ from TradingView indicators) |
| **52W high** | Distance below the 52-week high |
| **Checklist** | The nine trend-template rules |

### Sorting and quick filters

These work on the rows already loaded by the controls above and need no new scan.

- **Sort:** click the header of **Setup score**, **From pivot**, **Risk**, **Trend** or **RS**. The first click puts the best value on top (highest score, *lowest* risk); click again to reverse; a third click removes the sort. Rows with no value always stay at the bottom.
- **Filter chips** above the table (each shows how many stocks it matches; select several to combine):
  - **Stage** — Breakout, Ready, Recent breakout, Forming, … (only stages present in the current view are shown)
  - **Setup** — VCP / Power play
  - **Entry** — Cheat / Low cheat / Handle
  - **Pullbacks** — *Shakeout (SO)* shows only stocks with a shakeout in the base

  Within a group the chips are OR (Ready *or* Breakout); across groups they are AND (Power play **and** shakeout). **Clear filters** resets them. The counter at the right shows rows shown vs. loaded.

### Stages

| Stage | Meaning | Typical action |
|---|---|---|
| **Breakout** | Today's close crossed above the pivot | Check volume (⚠) and the chart; act if the breakout is clean |
| **Ready** | Valid tightening base; close within 5% (Power play / 4H: 3%) **below** the pivot | Add to watchlist, plan the entry and stop |
| **Recent breakout** | Broke out in the last few bars and still near the pivot | Possible late entry or pullback-to-pivot entry |
| **Forming** | A base exists but it is not tight enough yet (or price drifted above the pivot without a fresh crossing) | Keep an eye on it |
| **Extended** | More than 5% above the pivot | Do not chase |
| **Failed** | Closed back below the pivot / stop after a breakout | Avoid or exit |
| **No base** | No qualifying base | — |

## 3. The stock popup and annotated chart

Click a symbol to open the popup. The chart has a **Daily / 4H** toggle and shows:

| On the chart | Meaning |
|---|---|
| Blue / red thin lines | EMA10 / EMA20 |
| Light blue / green / orange lines | SMA50 / SMA150 / SMA200 |
| Yellow dashed lines | Base high and base low, from the start of the base |
| Thick yellow zig-zag | The swing highs and lows that define the contractions |
| `-12.3%` labels | Depth of each contraction at its low |
| `SO` arrow | Shakeout: the low undercut the previous low and was reclaimed |
| `Base` arrow | Left-side high where the base starts |
| `Breakout` arrow | Bar that closed above the pivot |
| Green / red dashed price lines | Pivot / Stop |
| Bottom pane | Volume with its 50-bar average |

The chart setup is recomputed from the latest cached bars for the selected timeframe, so after a new session it can differ slightly from last night's table. Below the chart are all setup details (prior rally, base start, volume dry-up, final tightness, breakout volume, F&O lot size, 1H power play) and the trend-template checklist.

**Reviewing a setup — suggested checklist**

1. Is there a clear prior rally into the base?
2. Do the pullbacks get smaller from left to right, and do the lows hold (or shake out and reclaim)?
3. Is volume drying up inside the base?
4. Is the risk to the stop acceptable for your position size?
5. For a breakout: did it come on volume (no ⚠)?

## 4. Telegram digest

Sent after the evening scan to the chat configured in the repository secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. It contains, for stocks with trend score ≥ 7, RS ≥ 60 and liquid:

- 🚀 Daily breakouts (all), with breakout volume and ⚠ for low volume
- 🎯 Top 10 Daily *Ready* setups with pivot, distance, stop and risk
- ⏱ 4H breakouts and the top 4H *Ready* setups
- ⭐ Watchlist stocks that are Breakout / Ready / Recent breakout / Failed

Tags in the digest: `F&O`, `SO` (shakeout), `1H ready` / `1H breakout`.

Preview it locally without sending:

```bash
uv run minervini notify --dry-run
```

Send it manually: `TELEGRAM_BOT_TOKEN=… TELEGRAM_CHAT_ID=… uv run minervini notify`.

## 5. Watchlist

Click the ☆ next to a symbol to save it. The watchlist is stored in `data/watchlist.db` (committed, so the nightly job can see it). The **Watchlist** button shows all saved stocks regardless of filters, with their current stage — a quick status check of everything you are tracking. Removing and re-adding a stock resets its "added" date.

## 6. Commands

| Command | Purpose |
|---|---|
| `uv run minervini update` | Daily + 4H scans (what the nightly job runs) |
| `uv run minervini scan -t daily` / `-t 4h` | One timeframe |
| `uv run minervini notify [--dry-run]` | Telegram digest |
| `uv run minervini journal-check trades.csv` | Replay the detector on past trade dates (`symbol,date` columns) — keep personal journals out of the repo |
| `uv run minervini update-fno` | Refresh the F&O lot-size list from NSE |
| `uv run minervini api` | Start the backend |

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Table says "No stocks match" | Run `make update` or `git pull` to get scan results; relax filters |
| Chart shows "No price data" | Symbol unknown to Yahoo or no network on first load |
| Daily values differ slightly from TradingView | Yahoo data; the latest daily bar is sometimes published late and is rebuilt from hourly bars (volume is estimated) |
| RS differs from the TradingView indicator | Different formula; this RS is a percentile within the liquid stocks of the scanned universe |
| 4H data missing for a recent IPO | Yahoo serves only ~1 year of hourly bars for those; the cache grows over time |
