import numpy as np
import pandas as pd
import pytest

from minervini_scanner.indicators import percentile_ratings, weighted_momentum_score


def test_percentile_ratings():
    ratings = percentile_ratings(
        {
            "A": 0.10,
            "B": 0.20,
            "C": 0.30,
        }
    )

    assert ratings["A"] < ratings["B"] < ratings["C"]
    assert ratings["C"] == 100.0


def test_percentile_ratings_can_rate_against_a_reference_group():
    scores = {"A": 0.10, "B": 0.20, "C": 0.30, "JUNK": -0.90}

    ratings = percentile_ratings(scores, reference={"A", "B", "C"})

    # The thin stock does not drag the liquid names down, and is itself rated at the bottom.
    assert ratings["A"] == pytest.approx(100 / 3)
    assert ratings["C"] == 100.0
    assert ratings["JUNK"] == 0.0


def test_weighted_momentum_score_requires_one_year():
    df = pd.DataFrame({"Close": np.arange(100, dtype=float)})

    assert np.isnan(weighted_momentum_score(df))
