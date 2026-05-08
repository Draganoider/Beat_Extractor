from __future__ import annotations

from beat_extractor.taps import clean_taps, estimate_calibration


def test_estimate_calibration_for_spacebar_and_mouse() -> None:
    expected = [0.0, 0.6, 1.2, 1.8]
    raw = []
    for time_sec in expected:
        raw.append({"time_sec": time_sec + 0.075, "input_kind": "spacebar"})
        raw.append({"time_sec": time_sec + 0.11, "input_kind": "mouse"})

    calibration = estimate_calibration(expected, raw)

    assert calibration["spacebar_latency_ms"] == 75.0
    assert calibration["mouse_latency_ms"] == 110.0


def test_clean_taps_subtracts_latency_and_removes_duplicates() -> None:
    raw = [
        {"time_sec": 1.10, "input_kind": "spacebar"},
        {"time_sec": 1.14, "input_kind": "mouse"},
        {"time_sec": 2.10, "input_kind": "spacebar"},
    ]
    calibration = {"spacebar_latency_ms": 100.0, "mouse_latency_ms": 120.0}

    cleaned = clean_taps(raw, calibration, duration_sec=3.0)

    assert cleaned == [
        {"time_sec": 1.0, "type": "hit", "input_kind": "spacebar"},
        {"time_sec": 2.0, "type": "hit", "input_kind": "spacebar"},
    ]

