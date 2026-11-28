"""Evening Telegram digest built from the scan CSVs and the watchlist."""

from __future__ import annotations

import html
import json
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

TELEGRAM_LIMIT = 4096
ACTIONABLE = ("Breakout", "Ready", "Recent breakout")


@dataclass(frozen=True)
class DigestFilters:
    min_score: int = 7
    min_rs: float = 60.0
    liquid_only: bool = True
    max_ready: int = 10
    max_four_hour: int = 6


def _number(value: object, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def _tags(row: pd.Series) -> str:
    tags = []
    if bool(row.get("F&O")):
        tags.append("F&amp;O")
    if isinstance(row.get("Shakeout"), str):
        tags.append("SO")
    if row.get("1H Stage") in ACTIONABLE:
        tags.append(f"1H {html.escape(str(row['1H Stage']).lower())}")
    return f" [{' · '.join(tags)}]" if tags else ""


def _line(row: pd.Series, *, breakout: bool) -> str:
    symbol = html.escape(str(row["Symbol"]))
    setup = html.escape(f"{row.get('Setup') or ''} {int(row.get('Setup Score') or 0)}".strip())
    text = f"<b>{symbol}</b>{_tags(row)} ₹{_number(row['Price'])} · pivot {_number(row['Pivot'])}"
    if breakout:
        volume = row.get("Breakout Volume x")
        warn = " ⚠" if isinstance(row.get("Setup Notes"), str) else ""
        text += f" · vol {_number(volume, 1)}×{warn}"
    else:
        text += f" ({_number(row['% From Pivot'], 1)}%) · stop {_number(row['Stop'])}"
        text += f" · risk {_number(row['Risk %'], 1)}%"
    return f"{text} · {setup}"


def _screen(df: pd.DataFrame, filters: DigestFilters) -> pd.DataFrame:
    if df.empty or "Stage" not in df.columns:
        return df.iloc[0:0]
    mask = (df["Score"] >= filters.min_score) & (df["RS Rating"] >= filters.min_rs)
    if filters.liquid_only and "Liquid" in df.columns:
        mask &= df["Liquid"].fillna(False).astype(bool)
    return df[mask]


def _section(title: str, rows: Iterable[str]) -> list[str]:
    rows = list(rows)
    return [f"\n<b>{title}</b>", *rows] if rows else []


def build_digest(
    daily: pd.DataFrame,
    four_hour: pd.DataFrame,
    watchlist: list[str],
    as_of: str,
    filters: DigestFilters | None = None,
) -> list[str]:
    """Telegram HTML messages, each within Telegram's length limit."""
    filters = filters or DigestFilters()
    screened = _screen(daily, filters)
    screened_4h = _screen(four_hour, filters)

    def by_stage(df: pd.DataFrame, stage: str) -> pd.DataFrame:
        if "Stage" not in df.columns:
            return df
        return df[df["Stage"] == stage].sort_values("Setup Score", ascending=False)

    breakouts = by_stage(screened, "Breakout")
    all_ready = by_stage(screened, "Ready")
    ready = all_ready.head(filters.max_ready)
    breakouts_4h = by_stage(screened_4h, "Breakout").head(filters.max_four_hour)
    ready_4h = by_stage(screened_4h, "Ready").head(filters.max_four_hour)

    lines = [
        f"<b>📈 Pivot Watch · {html.escape(as_of)}</b>",
        f"Trend ≥ {filters.min_score}/9 · RS ≥ {filters.min_rs:g}"
        + (" · liquid" if filters.liquid_only else ""),
    ]
    lines += _section(
        f"🚀 Daily breakouts ({len(breakouts)})",
        (_line(row, breakout=True) for _, row in breakouts.iterrows()),
    )
    lines += _section(
        f"🎯 Daily ready — top {len(ready)} of {len(all_ready)}",
        (_line(row, breakout=False) for _, row in ready.iterrows()),
    )
    lines += _section(
        "⏱ 4H breakouts",
        (_line(row, breakout=True) for _, row in breakouts_4h.iterrows()),
    )
    lines += _section(
        "⏱ 4H ready",
        (_line(row, breakout=False) for _, row in ready_4h.iterrows()),
    )

    watch_lines = []
    if "Stage" in daily.columns:
        alerts = daily[
            daily["Symbol"].isin(watchlist) & daily["Stage"].isin([*ACTIONABLE, "Failed"])
        ]
        for _, row in alerts.iterrows():
            label = "⚠️ failed breakout" if row["Stage"] == "Failed" else str(row["Stage"]).lower()
            watch_lines.append(
                f"<b>{html.escape(str(row['Symbol']))}</b>{_tags(row)} {html.escape(label)}"
                f" · ₹{_number(row['Price'])} · pivot {_number(row['Pivot'])}"
                f" · stop {_number(row['Stop'])}"
            )
    lines += _section(f"⭐ Watchlist ({len(watch_lines)} of {len(watchlist)})", watch_lines)

    if len(lines) == 2:
        lines.append("\nNo actionable setups today.")
    return split_messages(lines)


def split_messages(lines: list[str], limit: int = TELEGRAM_LIMIT) -> list[str]:
    messages: list[str] = []
    current = ""
    for line in lines:
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit and current:
            messages.append(current)
            current = line[:limit]
        else:
            current = candidate[:limit]
    if current:
        messages.append(current)
    return messages


def send_telegram(token: str, chat_id: str, messages: list[str], timeout: float = 20) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for message in messages:
        payload = json.dumps(
            {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
        ).encode()
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read())
        if not body.get("ok"):
            raise RuntimeError(f"Telegram API error: {body.get('description')}")
