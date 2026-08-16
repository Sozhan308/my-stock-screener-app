import numpy as np
import pandas as pd

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


def test_weighted_momentum_score_requires_one_year():
    df = pd.DataFrame({"Close": np.arange(100, dtype=float)})

    assert np.isnan(weighted_momentum_score(df))
