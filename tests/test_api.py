import pandas as pd
from fastapi.testclient import TestClient

from minervini_scanner import api


def test_stocks_filters_by_stage_setup_score_and_liquidity(tmp_path, monkeypatch):
    pd.DataFrame(
        [
            {
                "Symbol": "AAA",
                "Score": 9,
                "RS Rating": 90,
                "Stage": "Ready",
                "Setup Score": 80,
                "Liquid": True,
            },
            {
                "Symbol": "BBB",
                "Score": 9,
                "RS Rating": 90,
                "Stage": "Forming",
                "Setup Score": 90,
                "Liquid": True,
            },
            {
                "Symbol": "CCC",
                "Score": 9,
                "RS Rating": 90,
                "Stage": "Breakout",
                "Setup Score": 40,
                "Liquid": True,
            },
            {
                "Symbol": "DDD",
                "Score": 9,
                "RS Rating": 90,
                "Stage": "Ready",
                "Setup Score": 85,
                "Liquid": False,
            },
        ]
    ).to_csv(tmp_path / "minervini_daily.csv", index=False)
    monkeypatch.setattr(api.settings, "output_dir", tmp_path)

    response = TestClient(api.app).get(
        "/api/stocks",
        params={
            "stages": "Breakout,Ready",
            "min_setup_score": 50,
            "liquid_only": True,
        },
    )

    assert response.status_code == 200
    assert [row["Symbol"] for row in response.json()["stocks"]] == ["AAA"]


def test_chart_returns_candles_and_setup_geometry(tmp_path, monkeypatch):
    from minervini_scanner.store import MarketDataStore
    from test_setups import vcp_base

    MarketDataStore(tmp_path).save("TEST", "1d", vcp_base())
    monkeypatch.setattr(api.settings, "data_dir", tmp_path)
    monkeypatch.setattr(api, "YahooBatchDownloader", lambda **_: lambda *a, **k: {})

    response = TestClient(api.app).get("/api/chart/test", params={"bars": 60})

    data = response.json()
    assert response.status_code == 200
    assert data["setup"]["stage"] == "Ready"
    base = data["setup"]["base"]
    assert [round(c["depthPct"]) for c in base["contractions"]] == [15, 7, 3]
    times = [candle["time"] for candle in data["candles"]]
    assert base["start"] in times
    assert times[-1] == data["lines"]["EMA10"][-1]["time"]
