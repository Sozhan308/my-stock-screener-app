import pandas as pd

from minervini_scanner.data import complete_daily_from_hourly, resample_to_4h


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


def test_complete_daily_from_hourly_adds_missing_session_with_scaled_volume():
    daily = pd.DataFrame(
        {"Open": [10.0], "High": [11.0], "Low": [9.0], "Close": [10.5], "Volume": [1000.0]},
        index=pd.DatetimeIndex(["2026-01-05"]),
    )
    hourly_index = pd.DatetimeIndex(
        ["2026-01-05 09:15", "2026-01-05 10:15", "2026-01-06 09:15", "2026-01-06 10:15"],
        tz="Asia/Kolkata",
    )
    hourly = pd.DataFrame(
        {
            "Open": [10.0, 10.2, 10.6, 11.0],
            "High": [10.5, 11.0, 11.2, 11.5],
            "Low": [9.0, 10.1, 10.4, 10.9],
            "Close": [10.2, 10.5, 11.0, 11.3],
            "Volume": [400.0, 400.0, 300.0, 500.0],
        },
        index=hourly_index,
    )

    result = complete_daily_from_hourly(daily, hourly)

    assert result.index[-1] == pd.Timestamp("2026-01-06")
    assert result.iloc[-1][["Open", "High", "Low", "Close"]].tolist() == [10.6, 11.5, 10.4, 11.3]
    # Hourly bars captured 800 of 1000 shares on the overlapping day, so 800 -> 1000.
    assert result.iloc[-1]["Volume"] == 1000.0
    assert complete_daily_from_hourly(result, hourly).equals(result)
