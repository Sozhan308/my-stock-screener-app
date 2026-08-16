import pandas as pd

from minervini_scanner.data import resample_to_4h


def test_resample_to_4h():
    index = pd.date_range(
        "2026-01-05 09:15",
        periods=7,
        freq="1h",
        tz="Asia/Kolkata",
    )

    df = pd.DataFrame(
        {
            "Open": range(7),
            "High": range(1, 8),
            "Low": range(7),
            "Close": range(1, 8),
            "Volume": [100] * 7,
        },
        index=index,
    )

    result = resample_to_4h(df)

    assert not result.empty
    assert {"Open", "High", "Low", "Close", "Volume"} <= set(result.columns)
