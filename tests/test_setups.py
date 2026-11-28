import numpy as np
import pandas as pd
import pytest

from minervini_scanner.setups import (
    DAILY_POWER_PLAY,
    DAILY_VCP,
    Stage,
    detect_best_setup,
    detect_setup,
    find_swings,
)


def make_path(start: float, legs: list[tuple[int, float]], volume: float = 1_000.0) -> pd.DataFrame:
    """Daily OHLCV that moves linearly between waypoints; each leg is (bars, target close)."""
    closes = [start]
    for bars, target in legs:
        closes.extend(np.linspace(closes[-1], target, bars + 1)[1:])
    close = np.array(closes)
    index = pd.bdate_range("2025-01-01", periods=len(close))
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.004,
            "Low": close * 0.996,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


PRIOR = [(60, 100.0), (40, 140.0)]  # flat history, then a +40% rally


def vcp_base() -> pd.DataFrame:
    return make_path(
        100.0,
        PRIOR + [(8, 120.0), (8, 137.0), (6, 129.0), (5, 135.0), (4, 132.0), (4, 133.5)],
    )


def with_breakout(df: pd.DataFrame, close: float, volume: float) -> pd.DataFrame:
    bar = pd.DataFrame(
        {
            "Open": [df["Close"].iloc[-1]],
            "High": [close * 1.004],
            "Low": [df["Close"].iloc[-1] * 0.996],
            "Close": [close],
            "Volume": [volume],
        },
        index=[df.index[-1] + pd.offsets.BDay()],
    )
    return pd.concat([df, bar])


def test_find_swings_alternate_and_mark_open_leg_provisional():
    df = vcp_base()
    swings = find_swings(df["High"].to_numpy(), df["Low"].to_numpy(), order=3, min_swing_pct=1.5)

    kinds = [swing.kind for swing in swings]
    assert all(a != b for a, b in zip(kinds, kinds[1:], strict=False))
    assert swings[-1].provisional
    assert not any(swing.provisional for swing in swings[:-1])


def test_tightening_base_near_pivot_is_ready():
    result = detect_setup(vcp_base(), DAILY_VCP)

    assert result.stage is Stage.READY
    base = result.base
    assert base is not None and base.is_vcp
    assert [round(c.depth_pct) for c in base.contractions] == [15, 7, 3]
    assert base.pivot == 135.0 * 1.004
    assert base.stop == 132.0 * 0.996
    assert result.risk_pct == pytest.approx((base.pivot - base.stop) / base.pivot * 100)
    assert result.risk_pct == pytest.approx(3.0, abs=0.01)


def test_volume_breakout_above_pivot():
    result = detect_setup(with_breakout(vcp_base(), 137.0, 3_000.0), DAILY_VCP)

    assert result.stage is Stage.BREAKOUT
    assert result.breakout_volume_ratio == 3.0
    assert result.notes == ()


def test_low_volume_breakout_is_flagged():
    result = detect_setup(with_breakout(vcp_base(), 137.0, 1_000.0), DAILY_VCP)

    assert result.stage is Stage.BREAKOUT
    assert "breakout volume below threshold" in result.notes


def test_widening_pullbacks_are_not_a_vcp():
    df = make_path(
        100.0,
        PRIOR + [(5, 133.0), (5, 138.0), (8, 126.0), (5, 131.0)],
    )
    result = detect_setup(df, DAILY_VCP)

    assert result.stage is Stage.FORMING
    assert result.base is not None and not result.base.is_vcp


def test_reclaimed_undercut_is_a_shakeout():
    df = make_path(
        100.0,
        PRIOR + [(8, 126.0), (8, 137.0), (6, 125.0), (3, 131.0), (5, 135.0), (4, 133.0), (4, 134)],
    )
    result = detect_setup(df, DAILY_VCP)

    base = result.base
    assert base is not None and base.is_vcp
    assert base.shakeout is not None
    assert base.shakeout.low < base.contractions[0].low


def test_base_without_prior_rally_is_ignored():
    df = make_path(100.0, [(60, 100.0), (40, 110.0), (8, 100.0), (8, 108.0), (6, 104.0), (5, 107)])

    assert detect_setup(df, DAILY_VCP).stage is Stage.NO_BASE


def test_short_pause_after_sharp_run_is_a_power_play():
    df = make_path(100.0, [(60, 100.0), (20, 135.0), (2, 131.0), (2, 133.0), (1, 132.5)])

    assert detect_setup(df, DAILY_VCP).stage is Stage.NO_BASE
    result = detect_best_setup(df, (DAILY_VCP, DAILY_POWER_PLAY))
    assert result.setup_type == "Power play"
    assert result.stage is Stage.READY


def test_intraday_poke_above_pivot_does_not_hide_the_breakout():
    df = make_path(100.0, PRIOR + [(8, 120.0), (8, 130.0), (6, 124.0), (6, 133.0), (8, 132.4)])
    before = detect_setup(df, DAILY_VCP)
    assert before.stage is Stage.READY and before.base is not None

    poked = with_breakout(df, 133.2, 1_000.0)  # high trades above the pivot, close stays below
    assert poked["High"].iloc[-1] > before.base.pivot > poked["Close"].iloc[-1]
    result = detect_setup(with_breakout(poked, 134.5, 3_000.0), DAILY_VCP)

    assert result.stage is Stage.BREAKOUT
    assert result.base is not None and result.base.pivot == before.base.pivot


def test_price_above_pivot_is_never_ready():
    df = vcp_base()
    base = detect_setup(df, DAILY_VCP).base
    assert base is not None

    for step in range(14):
        df = with_breakout(df, base.pivot * (1.005 + 0.0015 * step), 1_000.0)
        assert detect_setup(df, DAILY_VCP).stage is not Stage.READY
