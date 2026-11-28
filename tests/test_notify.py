import pandas as pd

from minervini_scanner.notify import build_digest, split_messages


def row(symbol: str, stage: str, **overrides) -> dict:
    data = {
        "Symbol": symbol,
        "Price": 100.0,
        "Score": 9,
        "RS Rating": 80.0,
        "Liquid": True,
        "Stage": stage,
        "Setup": "VCP",
        "Setup Score": 70,
        "Pivot": 101.0,
        "Stop": 95.0,
        "Risk %": 5.9,
        "% From Pivot": -1.0,
        "Breakout Volume x": 2.1,
        "Setup Notes": None,
        "Shakeout": None,
        "1H Stage": None,
        "F&O": False,
    }
    return data | overrides


def test_digest_lists_screened_setups_and_watchlist_alerts():
    daily = pd.DataFrame(
        [
            row("M&M", "Breakout", **{"F&O": True}),
            row("READY1", "Ready", Shakeout="2026-11-20"),
            row("ILLIQ", "Breakout", Liquid=False),
            row("WEAK", "Ready", Score=5),
            row("WATCHED", "Failed", Score=4),
        ]
    )

    text = "\n".join(build_digest(daily, pd.DataFrame(), ["WATCHED"], as_of="27 Nov 2026"))

    assert "<b>M&amp;M</b> [F&amp;O]" in text
    assert "READY1</b> [SO]" in text
    assert "ILLIQ" not in text and "WEAK" not in text
    assert "WATCHED</b> ⚠️ failed breakout" in text


def test_split_messages_respects_limit():
    messages = split_messages([f"line {i} " + "x" * 50 for i in range(200)], limit=1000)

    assert len(messages) > 1
    assert all(len(message) <= 1000 for message in messages)
    assert sum(message.count("line ") for message in messages) == 200
