# Setup detection

Source: [`src/minervini_scanner/setups.py`](../src/minervini_scanner/setups.py)

The detector answers one question for every stock and timeframe: *is there a rally → tightening base → breakout setup, and where is it in its life cycle?* All lengths are counted in **bars**, so the same code runs on Daily, 4H and 1H candles with different presets.

## 1. Pipeline

1. **Swings (zig-zag).** A bar is a swing high/low when it is the extreme of the `swing_order` bars on both sides. Consecutive swings of the same kind keep the more extreme one, and a swing must move at least `min_swing_pct` from the previous swing. The bars after the last confirmed swing are walked one by one as *provisional* swings, so the in-progress pullback is visible. A confirmed swing is never moved: once price trades through it without a meaningful counter-move the walk stops, so the broken level stays available as the pivot.
2. **Base start (left-side high).** Candidates are swing highs that have not been exceeded since, between `base_min_bars` and `base_max_bars` ago. The **oldest** candidate that satisfies both rules below is chosen, so the base spans all of its contractions:
   - depth from the left-side high to the lowest low since ≤ `base_max_depth_pct`
   - prior rally: left-side high ≥ `rally_min_pct` above the lowest low of the preceding `rally_max_bars`
3. **Contractions.** Every swing high → next swing low inside the base is a contraction (pullback) with a depth in %. A low that undercuts the previous contraction low by ≤ `shakeout_max_undercut_pct` and closes back above it within `shakeout_reclaim_bars` bars is a **shakeout**.
4. **VCP rule.** Starting from the deepest contraction, each following contraction must be no deeper than the previous one × `contraction_tolerance`, and lows must not undercut the previous low unless it is a shakeout. Shakeout legs are exempt from the tightening rule (an undercut is deeper by design). At least `min_contractions` contractions are required from the deepest one onwards.
5. **Pivot and stop.** Pivot = most recent *confirmed* swing high in the base. Stop = lowest low since that pivot (the low of the latest contraction). Risk % = (pivot − stop) / pivot.
6. **Entry zone.** Where the pivot sits in the base range (low → left-side high): lower third *Low cheat*, middle third *Cheat*, upper third *Handle*.
7. **Breakout check.** For each of the last `breakout_lookback_bars` bars the base is re-evaluated **as of the previous bar** (no lookahead). A breakout is the first close above that pivot after a close at or below it. Volume ≥ `breakout_volume_mult` × the previous `volume_avg_bars` average confirms it; otherwise the result carries the note *breakout volume below threshold* (⚠).
8. **Stage** (see below) and **score**.

Multiple presets run per timeframe; the most actionable result wins (Breakout > Ready > Recent breakout > Forming > Extended > Failed > No base), ties broken by score.

## 2. Presets

| Parameter | Daily VCP | Daily Power play | 4H VCP | 1H power play (hint) |
|---|---|---|---|---|
| Swing order / min swing | 3 / 1.5% | 2 / 0.75% | 3 / 1.0% | 2 / 0.5% |
| Prior rally | ≥ 25% within 63 bars | ≥ 25% within 40 bars | ≥ 15% within 60 bars | ≥ 8% within 70 bars |
| Base length | 15 – 252 bars | 2 – 15 bars | 8 – 150 bars | 4 – 35 bars |
| Max base depth | 20% | 10% | 15% | 5% |
| Min contractions | 2 | 1 | 2 | 1 |
| Tightening tolerance | 1.1× | 1.1× | 1.1× | 1.1× |
| Shakeout | undercut ≤ 3%, reclaimed ≤ 3 bars | same | same | same |
| Ready if below pivot by | ≤ 5% | ≤ 3% | ≤ 3% | ≤ 1.5% |
| Breakout volume | ≥ 1.5× 50-bar avg | same | same | same |
| Breakout lookback | 5 bars | 3 bars | 4 bars | 3 bars |
| Extended / Failed | > 5% above / > 3% below pivot | 5% / 3% | 4% / 2% | 3% / 1.5% |

Daily scans use *Daily VCP* + *Daily Power play*; 4H scans use *4H VCP*; both scans also report the *1H power play* as a hint (`1H Stage`, `1H Pivot` columns and the purple **1H** tag).

## 3. Stages

| Stage | Rule |
|---|---|
| **Breakout** | The last bar closed above the pivot (after closing at/below it) |
| **Recent breakout** | Breakout within the lookback window and still between the failed and extended thresholds |
| **Extended** | Breakout within the window and now more than the extended threshold above the pivot |
| **Failed** | Breakout within the window, now below the stop or more than the failed threshold below the pivot |
| **Ready** | Valid VCP and close between `−pivot_proximity_pct` and 0% from the pivot |
| **Forming** | A base exists but the VCP rule fails, the close is too far below the pivot, or the close is above the pivot without a crossing in the window |
| **No base** | No candidate left-side high satisfies the rally and depth rules |

## 4. Setup score (0–100)

| Component | Points |
|---|---|
| Valid VCP | 15 |
| Contractions from the deepest one: 1 / 2 / 3 / 4+ | 3 / 8 / 12 / 15 |
| Final contraction depth ≤ 3% / ≤ 6% / ≤ 10% / more | 20 / 14 / 8 / 3 |
| Volume dry-up (10-bar ÷ 50-bar average) ≤ 0.6 / ≤ 0.8 / ≤ 1.0 | 15 / 10 / 5 |
| Prior rally (linear up to 50%) | 0 – 10 |
| Breakout or recent breakout (5 if volume below threshold); otherwise distance below pivot ≤ 2% / ≤ 5% / ≤ 10% | 15 / 10 / 4 |
| Shakeout in the tightening part of the base | 5 |
| Base depth ≤ 10% / ≤ 15% | 5 / 3 |

The score ranks setups for review; it is not a probability of success. Backtesting (see the [roadmap](roadmap.md)) is planned to tune these weights.

## 5. Data handling

- Bars come from the local Parquet cache (`data/cache/`), refreshed incrementally from Yahoo Finance.
- Yahoo often publishes the latest NSE daily bar late (prices empty, volume present). Missing trailing daily sessions are rebuilt from hourly bars; because hourly bars capture only ~75% of daily volume, the rebuilt volume is scaled by the stock's own hourly/daily volume ratio over the last 20 sessions.
- 4H candles are resampled from hourly bars at 09:15 and 13:15 IST.

## 6. Validation

- **Synthetic tests** (`tests/test_setups.py`) cover tightening vs widening bases, shakeouts, missing rally, volume/low-volume breakouts, intraday pokes above the pivot, and price above the pivot never being *Ready*.
- **Historical trade entries.** The thresholds were calibrated against a private set of 24 historical swing-trade entries (May–Aug 2026), using `minervini journal-check`:
  - 19 of 24 were flagged as Ready / Breakout / Recent breakout on Daily or 4H at the close before the entry or on the entry day (this is what `journal-check` reports); 21 of 24 when the 1H hint is also checked hour by hour through the entry day.
  - In 9 cases the detected pivot was within ~0.5% of the level drawn by hand on the chart.
  - The strict "every pullback shallower than the last" rule rejected many of these entries, which led to the *from the deepest contraction* rule, the 10% tolerance and the shakeout exemption.
- **Noise level.** On a typical day 30–70 stocks are actionable on Daily with trend score ≥ 7, versus ~190 stocks that pass the trend template alone.
