from __future__ import annotations

from typing import Iterable

import pandas as pd

from beat_extractor.models import event_id


def events_to_editor_rows(events: Iterable[dict]) -> pd.DataFrame:
    rows = []
    for event in events:
        rows.append(
            {
                "enabled": True,
                "id": event["id"],
                "time_sec": float(event["time_sec"]),
                "type": event["type"],
                "strength": float(event["strength"]),
                "confidence": float(event["confidence"]),
                "source": event["source"],
                "edited": bool(event.get("edited", False)),
            }
        )
    return pd.DataFrame(rows, columns=["enabled", "id", "time_sec", "type", "strength", "confidence", "source", "edited"])


def events_from_editor(rows, duration_sec: float) -> list[dict]:
    if rows is None:
        return []
    dataframe = pd.DataFrame(rows)
    events = []
    for _, row in dataframe.iterrows():
        if "enabled" in row and not bool(row.get("enabled", True)):
            continue
        time_sec = _clamp_float(row.get("time_sec", 0.0), 0.0, duration_sec)
        strength = _clamp_float(row.get("strength", 0.75), 0.0, 1.0)
        confidence = _clamp_float(row.get("confidence", 0.75), 0.0, 1.0)
        source = str(row.get("source") or "onset")
        if source not in {"beat", "onset", "downbeat", "section"}:
            source = "onset"
        events.append(
            {
                "id": str(row.get("id") or ""),
                "time_sec": round(time_sec, 6),
                "type": "hit",
                "strength": round(strength, 6),
                "confidence": round(confidence, 6),
                "source": source,
                "edited": True,
            }
        )

    events.sort(key=lambda item: item["time_sec"])
    for index, event in enumerate(events, start=1):
        event["id"] = event_id(index)
    return events


def _clamp_float(value, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = low
    return max(low, min(high, number))

