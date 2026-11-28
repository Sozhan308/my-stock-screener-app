"""Rally -> volatility contraction -> breakout setup detection.

Lengths are expressed in bars so the same logic runs on Daily and 4H candles. Two setup
families are detected:

* ``VCP``: a multi-week base after a strong rally, with successively tighter pullbacks.
* ``Power play``: a short, tight pause just below the high after a sharp run-up.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum

import numpy as np
import pandas as pd


class Stage(StrEnum):
    NO_BASE = "No base"
    FORMING = "Forming"
    READY = "Ready"
    BREAKOUT = "Breakout"
    RECENT_BREAKOUT = "Recent breakout"
    EXTENDED = "Extended"
    FAILED = "Failed"


# Lower number = more actionable; used to pick the best result across presets.
STAGE_PRIORITY: dict[Stage, int] = {
    Stage.BREAKOUT: 0,
    Stage.READY: 1,
    Stage.RECENT_BREAKOUT: 2,
    Stage.FORMING: 3,
    Stage.EXTENDED: 4,
    Stage.FAILED: 5,
    Stage.NO_BASE: 6,
}

ACTIONABLE_STAGES = frozenset({Stage.BREAKOUT, Stage.READY, Stage.RECENT_BREAKOUT})


class EntryZone(StrEnum):
    LOW_CHEAT = "Low cheat"
    CHEAT = "Cheat"
    HANDLE = "Handle"


@dataclass(frozen=True)
class SetupParams:
    name: str = "VCP"
    swing_order: int = 3
    min_swing_pct: float = 1.5
    rally_min_pct: float = 25.0
    rally_max_bars: int = 63
    base_min_bars: int = 15
    base_max_bars: int = 252
    base_max_depth_pct: float = 20.0
    min_contractions: int = 2
    # Each contraction may be at most this multiple of the previous one (1.0 = strict).
    contraction_tolerance: float = 1.1
    # A contraction low may undercut the previous low by this much if it is quickly reclaimed.
    shakeout_max_undercut_pct: float = 3.0
    shakeout_reclaim_bars: int = 3
    pivot_proximity_pct: float = 5.0
    breakout_volume_mult: float = 1.5
    volume_avg_bars: int = 50
    dryup_bars: int = 10
    tightness_bars: int = 5
    breakout_lookback_bars: int = 5
    extended_pct: float = 5.0
    failed_pct: float = 3.0


DAILY_VCP = SetupParams()

DAILY_POWER_PLAY = SetupParams(
    name="Power play",
    swing_order=2,
    min_swing_pct=0.75,
    rally_min_pct=25.0,
    rally_max_bars=40,
    base_min_bars=2,
    base_max_bars=15,
    base_max_depth_pct=10.0,
    min_contractions=1,
    pivot_proximity_pct=3.0,
    tightness_bars=3,
    breakout_lookback_bars=3,
)

FOUR_HOUR_VCP = SetupParams(
    swing_order=3,
    min_swing_pct=1.0,
    rally_min_pct=15.0,
    rally_max_bars=60,
    base_min_bars=8,
    base_max_bars=150,
    base_max_depth_pct=15.0,
    pivot_proximity_pct=3.0,
    tightness_bars=6,
    breakout_lookback_bars=4,
    extended_pct=4.0,
    failed_pct=2.0,
)

# A 0.5-5 day pause just below the high after a sharp hourly run; shown as a hint only.
HOURLY_POWER_PLAY = SetupParams(
    name="1H power play",
    swing_order=2,
    min_swing_pct=0.5,
    rally_min_pct=8.0,
    rally_max_bars=70,
    base_min_bars=4,
    base_max_bars=35,
    base_max_depth_pct=5.0,
    min_contractions=1,
    pivot_proximity_pct=1.5,
    dryup_bars=7,
    tightness_bars=7,
    breakout_lookback_bars=3,
    extended_pct=3.0,
    failed_pct=1.5,
)

DAILY_PRESETS: tuple[SetupParams, ...] = (DAILY_VCP, DAILY_POWER_PLAY)
FOUR_HOUR_PRESETS: tuple[SetupParams, ...] = (FOUR_HOUR_VCP,)
HOURLY_PRESETS: tuple[SetupParams, ...] = (HOURLY_POWER_PLAY,)


@dataclass(frozen=True)
class Swing:
    index: int
    price: float
    kind: str  # "H" or "L"
    provisional: bool = False


@dataclass(frozen=True)
class Contraction:
    high_index: int
    high: float
    low_index: int
    low: float
    high_date: pd.Timestamp
    low_date: pd.Timestamp
    shakeout: bool = False

    @property
    def depth_pct(self) -> float:
        return (self.high - self.low) / self.high * 100


@dataclass(frozen=True)
class Base:
    start_index: int
    end_index: int
    start_date: pd.Timestamp
    high: float
    low: float
    rally_pct: float
    contractions: tuple[Contraction, ...]
    pivot: float
    pivot_date: pd.Timestamp
    stop: float
    is_vcp: bool

    @property
    def bars(self) -> int:
        return self.end_index - self.start_index

    @property
    def depth_pct(self) -> float:
        return (self.high - self.low) / self.high * 100

    @property
    def shakeout(self) -> Contraction | None:
        """Most recent shakeout within the tightening part of the base (from the deepest leg)."""
        return next((c for c in reversed(vcp_sequence(self.contractions)) if c.shakeout), None)

    @property
    def entry_zone(self) -> EntryZone:
        span = self.high - self.low
        position = (self.pivot - self.low) / span if span > 0 else 1.0
        if position < 1 / 3:
            return EntryZone.LOW_CHEAT
        if position < 2 / 3:
            return EntryZone.CHEAT
        return EntryZone.HANDLE


@dataclass(frozen=True)
class SetupResult:
    stage: Stage
    setup_type: str | None = None
    base: Base | None = None
    breakout_date: pd.Timestamp | None = None
    breakout_volume_ratio: float | None = None
    volume_dryup: float | None = None
    tightness_pct: float | None = None
    pct_from_pivot: float | None = None
    score: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def risk_pct(self) -> float | None:
        if self.base is None or self.base.pivot <= 0:
            return None
        return (self.base.pivot - self.base.stop) / self.base.pivot * 100


def find_swings(
    high: np.ndarray,
    low: np.ndarray,
    order: int,
    min_swing_pct: float,
) -> list[Swing]:
    """Alternating swing highs/lows (a zig-zag).

    Fractal pivots need ``order`` bars on both sides; the bars after the last confirmed pivot
    are walked as provisional swings so the in-progress leg is visible.
    """
    n = len(high)
    if n == 0:
        return []

    window = 2 * order + 1
    rolling_high = pd.Series(high).rolling(window, center=True, min_periods=1).max().to_numpy()
    rolling_low = pd.Series(low).rolling(window, center=True, min_periods=1).min().to_numpy()

    swings: list[Swing] = []

    def push(candidate: Swing) -> bool:
        if not swings:
            swings.append(candidate)
            return True
        last = swings[-1]
        if candidate.kind == last.kind:
            if candidate.kind == "H":
                more_extreme = candidate.price > last.price
            else:
                more_extreme = candidate.price < last.price
            if more_extreme:
                swings[-1] = candidate
            return more_extreme
        if abs(candidate.price / last.price - 1) * 100 >= min_swing_pct:
            swings.append(candidate)
            return True
        return False

    for i in range(n - order):
        is_high = high[i] >= rolling_high[i]
        is_low = low[i] <= rolling_low[i]
        if is_high and is_low:
            # Outside bar: emit the side that continues the alternation first.
            pair = [Swing(i, float(high[i]), "H"), Swing(i, float(low[i]), "L")]
            if swings and swings[-1].kind == "H":
                pair.reverse()
            for candidate in pair:
                push(candidate)
        elif is_high:
            push(Swing(i, float(high[i]), "H"))
        elif is_low:
            push(Swing(i, float(low[i]), "L"))

    # Walk the unconfirmed tail bar by bar. A confirmed swing is never moved: once price
    # trades through it without a meaningful counter-move, the walk stops so the confirmed
    # level stays available as the pivot (or support) that was broken.
    start = swings[-1].index + 1 if swings else n
    for i in range(start, n):
        last = swings[-1]
        if last.kind == "H":
            if high[i] > last.price:
                if not last.provisional:
                    break
                swings[-1] = Swing(i, float(high[i]), "H", provisional=True)
            elif (last.price - low[i]) / last.price * 100 >= min_swing_pct:
                swings.append(Swing(i, float(low[i]), "L", provisional=True))
        else:
            if low[i] < last.price:
                if not last.provisional:
                    break
                swings[-1] = Swing(i, float(low[i]), "L", provisional=True)
            elif (high[i] - last.price) / last.price * 100 >= min_swing_pct:
                swings.append(Swing(i, float(high[i]), "H", provisional=True))

    return swings


def _contractions(
    swings: Sequence[Swing],
    close: np.ndarray,
    dates: pd.Index,
    params: SetupParams,
) -> list[Contraction]:
    """High->low legs; a leg that undercuts the previous low and is reclaimed is a shakeout."""
    result: list[Contraction] = []
    for first, second in zip(swings, swings[1:], strict=False):
        if first.kind != "H" or second.kind != "L":
            continue
        shakeout = False
        if result and second.price < result[-1].low:
            previous_low = result[-1].low
            undercut = (previous_low - second.price) / previous_low * 100
            end = min(len(close), second.index + params.shakeout_reclaim_bars + 1)
            reclaimed = bool((close[second.index : end] > previous_low).any())
            shakeout = undercut <= params.shakeout_max_undercut_pct and reclaimed
        result.append(
            Contraction(
                high_index=first.index,
                high=first.price,
                low_index=second.index,
                low=second.price,
                high_date=dates[first.index],
                low_date=dates[second.index],
                shakeout=shakeout,
            )
        )
    return result


def vcp_sequence(contractions: Sequence[Contraction]) -> Sequence[Contraction]:
    """The contractions from the deepest one onwards; earlier, shallower legs are base noise."""
    if not contractions:
        return contractions
    depths = [c.depth_pct for c in contractions]
    return contractions[int(np.argmax(depths)) :]


def is_vcp(contractions: Sequence[Contraction], params: SetupParams) -> bool:
    """Contractions from the deepest one onwards must tighten, with rising (or shaken-out) lows.

    Shakeout legs are exempt from the tightening rule because an undercut is deeper by design.
    """
    sequence = vcp_sequence(contractions)
    if len(sequence) < params.min_contractions:
        return False

    reference = sequence[0]
    for current in sequence[1:]:
        if current.low < reference.low and not current.shakeout:
            return False
        if current.shakeout:
            continue
        if current.depth_pct > reference.depth_pct * params.contraction_tolerance:
            return False
        reference = current
    return True


def analyze_base(df: pd.DataFrame, params: SetupParams) -> Base | None:
    """Find the consolidation that ends at the last bar of ``df`` (no lookahead)."""
    n = len(df)
    if n < params.base_min_bars + params.swing_order + 2:
        return None

    high = df["High"].to_numpy(dtype=float)
    low = df["Low"].to_numpy(dtype=float)
    close = df["Close"].to_numpy(dtype=float)
    swings = find_swings(high, low, params.swing_order, params.min_swing_pct)

    suffix_high = np.maximum.accumulate(high[::-1])[::-1]
    window_start = max(0, n - 1 - params.base_max_bars)
    latest_start = n - 1 - params.base_min_bars

    candidates = [
        position
        for position, swing in enumerate(swings)
        if swing.kind == "H"
        and window_start <= swing.index <= latest_start
        and high[swing.index] >= suffix_high[swing.index]
    ]

    # Oldest valid left-side high first: it spans the full base and all its contractions.
    for position in candidates:
        start = swings[position]
        i0 = start.index
        base_low = float(low[i0 + 1 :].min())
        if (start.price - base_low) / start.price * 100 > params.base_max_depth_pct:
            continue

        rally_low = float(low[max(0, i0 - params.rally_max_bars) : i0 + 1].min())
        rally_pct = (start.price / rally_low - 1) * 100
        if rally_pct < params.rally_min_pct:
            continue

        base_swings = swings[position:]
        contractions = _contractions(base_swings, close, df.index, params)
        if not contractions:
            continue

        confirmed_highs = [s for s in base_swings if s.kind == "H" and not s.provisional]
        pivot = confirmed_highs[-1] if confirmed_highs else start
        stop = float(low[pivot.index + 1 :].min()) if pivot.index < n - 1 else base_low

        return Base(
            start_index=i0,
            end_index=n - 1,
            start_date=df.index[i0],
            high=start.price,
            low=base_low,
            rally_pct=rally_pct,
            contractions=tuple(contractions),
            pivot=pivot.price,
            pivot_date=df.index[pivot.index],
            stop=stop,
            is_vcp=is_vcp(contractions, params),
        )

    return None


def _volume_dryup(volume: np.ndarray, params: SetupParams) -> float | None:
    if len(volume) < params.volume_avg_bars:
        return None
    baseline = volume[-params.volume_avg_bars :].mean()
    if baseline <= 0:
        return None
    return float(volume[-params.dryup_bars :].mean() / baseline)


def _tightness(df: pd.DataFrame, params: SetupParams) -> float:
    recent = df.iloc[-params.tightness_bars :]
    return float((recent["High"].max() - recent["Low"].min()) / recent["Close"].iloc[-1] * 100)


def score_setup(result: SetupResult) -> int:
    base = result.base
    if base is None:
        return 0

    score = 0.0
    if base.is_vcp:
        score += 15
    score += {0: 0, 1: 3, 2: 8, 3: 12}.get(len(vcp_sequence(base.contractions)), 15)

    last_depth = base.contractions[-1].depth_pct if base.contractions else base.depth_pct
    score += 20 if last_depth <= 3 else 14 if last_depth <= 6 else 8 if last_depth <= 10 else 3

    if result.volume_dryup is not None:
        dryup = result.volume_dryup
        score += 15 if dryup <= 0.6 else 10 if dryup <= 0.8 else 5 if dryup <= 1.0 else 0

    score += min(base.rally_pct / 50, 1.0) * 10

    if result.stage in (Stage.BREAKOUT, Stage.RECENT_BREAKOUT):
        score += 5 if result.notes else 15
    elif result.pct_from_pivot is not None:
        distance = -result.pct_from_pivot
        score += 15 if distance <= 2 else 10 if distance <= 5 else 4 if distance <= 10 else 0

    if base.shakeout is not None:
        score += 5
    score += 5 if base.depth_pct <= 10 else 3 if base.depth_pct <= 15 else 0
    return int(round(min(score, 100)))


def detect_setup(df: pd.DataFrame, params: SetupParams = DAILY_VCP) -> SetupResult:
    """Classify the current state of ``df`` (OHLCV, oldest first) for one setup preset."""
    df = df.dropna(subset=["High", "Low", "Close"])
    history_bars = (
        params.base_max_bars
        + params.rally_max_bars
        + params.breakout_lookback_bars
        + 2 * params.swing_order
        + 10
    )
    df = df.iloc[-max(history_bars, params.volume_avg_bars + 1) :]
    n = len(df)
    if n < params.base_min_bars + params.swing_order + 2:
        return SetupResult(stage=Stage.NO_BASE)

    close = df["Close"].to_numpy(dtype=float)
    volume = df["Volume"].fillna(0).to_numpy(dtype=float)
    last_close = float(close[-1])

    first_check = max(
        params.base_min_bars + params.swing_order + 2,
        n - params.breakout_lookback_bars - 1,
    )
    for b in range(first_check, n):
        prior = df.iloc[:b]
        base = analyze_base(prior, params)
        if base is None or not base.is_vcp:
            continue
        if close[b] <= base.pivot or close[b - 1] > base.pivot:
            continue

        history = volume[max(0, b - params.volume_avg_bars) : b]
        avg_volume = history.mean() if len(history) else 0.0
        volume_ratio = float(volume[b] / avg_volume) if avg_volume > 0 else None
        pct_from_pivot = (last_close / base.pivot - 1) * 100

        notes: list[str] = []
        if volume_ratio is None or volume_ratio < params.breakout_volume_mult:
            notes.append("breakout volume below threshold")

        if b == n - 1:
            stage = Stage.BREAKOUT
        elif last_close < base.stop or pct_from_pivot < -params.failed_pct:
            stage = Stage.FAILED
        elif pct_from_pivot > params.extended_pct:
            stage = Stage.EXTENDED
        else:
            stage = Stage.RECENT_BREAKOUT

        return _with_score(
            SetupResult(
                stage=stage,
                setup_type=params.name,
                base=base,
                breakout_date=df.index[b],
                breakout_volume_ratio=volume_ratio,
                volume_dryup=_volume_dryup(volume[:b], params),
                tightness_pct=_tightness(prior, params),
                pct_from_pivot=pct_from_pivot,
                notes=tuple(notes),
            )
        )

    base = analyze_base(df, params)
    if base is None:
        return SetupResult(stage=Stage.NO_BASE)

    pct_from_pivot = (last_close / base.pivot - 1) * 100
    # Above the pivot without a crossing in the lookback window means the breakout is stale.
    ready = base.is_vcp and -params.pivot_proximity_pct <= pct_from_pivot <= 0
    return _with_score(
        SetupResult(
            stage=Stage.READY if ready else Stage.FORMING,
            setup_type=params.name,
            base=base,
            volume_dryup=_volume_dryup(volume, params),
            tightness_pct=_tightness(df, params),
            pct_from_pivot=pct_from_pivot,
        )
    )


def detect_best_setup(df: pd.DataFrame, presets: Sequence[SetupParams]) -> SetupResult:
    """Run every preset and keep the most actionable (then highest scoring) result."""
    results = [detect_setup(df, params) for params in presets]
    return min(results, key=lambda r: (STAGE_PRIORITY[r.stage], -r.score))


def _with_score(result: SetupResult) -> SetupResult:
    return replace(result, score=score_setup(result))
