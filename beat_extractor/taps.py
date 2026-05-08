from __future__ import annotations

from statistics import median


SUPPORTED_INPUTS = {"spacebar", "mouse"}
DUPLICATE_WINDOW_SEC = 0.09


def normalize_raw_taps(raw_taps: list[dict]) -> list[dict]:
    normalized = []
    for tap in raw_taps or []:
        try:
            time_sec = float(tap.get("time_sec", tap.get("time", 0.0)))
        except (TypeError, ValueError):
            continue
        input_kind = str(tap.get("input_kind") or "spacebar")
        if input_kind not in SUPPORTED_INPUTS:
            continue
        normalized.append({"time_sec": round(time_sec, 6), "input_kind": input_kind})
    return sorted(normalized, key=lambda item: item["time_sec"])


def estimate_input_latency_ms(
    expected_times: list[float],
    raw_taps: list[dict],
    input_kind: str,
    *,
    max_match_offset_sec: float = 0.35,
) -> float | None:
    taps = [tap["time_sec"] for tap in normalize_raw_taps(raw_taps) if tap["input_kind"] == input_kind]
    expected = [float(time_sec) for time_sec in expected_times]
    if not taps or not expected:
        return None

    used: set[int] = set()
    offsets = []
    for expected_time in expected:
        best_index = None
        best_distance = max_match_offset_sec
        for index, tap_time in enumerate(taps):
            if index in used:
                continue
            distance = abs(tap_time - expected_time)
            if distance <= best_distance:
                best_distance = distance
                best_index = index
        if best_index is not None:
            used.add(best_index)
            offsets.append(taps[best_index] - expected_time)

    if not offsets:
        return None
    return round(float(median(offsets) * 1000.0), 3)


def estimate_calibration(expected_times: list[float], raw_taps: list[dict]) -> dict:
    return {
        "spacebar_latency_ms": estimate_input_latency_ms(expected_times, raw_taps, "spacebar"),
        "mouse_latency_ms": estimate_input_latency_ms(expected_times, raw_taps, "mouse"),
    }


def calibration_is_ready(calibration: dict) -> bool:
    return calibration.get("spacebar_latency_ms") is not None and calibration.get("mouse_latency_ms") is not None


def clean_taps(
    raw_taps: list[dict],
    calibration: dict,
    duration_sec: float,
    *,
    duplicate_window_sec: float = DUPLICATE_WINDOW_SEC,
) -> list[dict]:
    cleaned = []
    for tap in normalize_raw_taps(raw_taps):
        offset_ms = calibration.get(f"{tap['input_kind']}_latency_ms")
        if offset_ms is None:
            continue
        time_sec = tap["time_sec"] - float(offset_ms) / 1000.0
        time_sec = max(0.0, min(float(duration_sec), time_sec))
        cleaned.append(
            {
                "time_sec": round(time_sec, 6),
                "type": "hit",
                "input_kind": tap["input_kind"],
            }
        )

    cleaned.sort(key=lambda item: item["time_sec"])
    deduped: list[dict] = []
    for event in cleaned:
        if deduped and event["time_sec"] - deduped[-1]["time_sec"] < duplicate_window_sec:
            continue
        deduped.append(event)
    return deduped

