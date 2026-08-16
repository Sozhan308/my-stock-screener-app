import numpy as np
import pandas as pd

from minervini_scanner.rules import evaluate_checklist


def make_frame(rows: int = 260) -> pd.DataFrame:
    close = np.linspace(100, 200, rows)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 2,
            "Low": close - 2,
            "Close": close,
            "Volume": 1000,
            "MA50": close - 5,
            "MA150": close - 10,
            "MA200": close - 20,
            "52W_HIGH": close + 10,
            "52W_LOW": close - 40,
        }
    )


def test_all_rules_can_pass():
    tf = make_frame()
    daily = make_frame()

    result = evaluate_checklist(
        tf,
        daily,
        rs_rating=90,
        rs_threshold=70,
        slope_periods=22,
    )

    assert result.score == 9
    assert result.ma200_rising


def test_low_rs_fails_only_rs_rule():
    tf = make_frame()
    daily = make_frame()

    result = evaluate_checklist(
        tf,
        daily,
        rs_rating=50,
        rs_threshold=70,
        slope_periods=22,
    )

    assert result.score == 8
    assert not result.rs_above_threshold
