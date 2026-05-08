from __future__ import annotations

import numpy as np

from auto_determining.generator import generate_beatmap_from_audio


def test_silence_produces_no_events_and_low_confidence() -> None:
    beatmap = generate_beatmap_from_audio(np.zeros(22050 * 6, dtype=np.float32), 22050)

    assert beatmap["events"] == []
    assert beatmap["analysis"]["confidence"] <= 0.05


def test_click_track_produces_hits_near_clicks(click_track) -> None:
    samples, expected_times = click_track()
    beatmap = generate_beatmap_from_audio(samples, 22050, target_events_per_minute=150)
    event_times = np.array([event["time_sec"] for event in beatmap["events"]], dtype=np.float32)

    assert len(event_times) >= len(expected_times) - 2
    matched = sum(np.min(np.abs(event_times - expected)) <= 0.08 for expected in expected_times)
    assert matched >= len(expected_times) - 2


def test_tempo_change_keeps_local_timing_stable(tempo_change_track) -> None:
    samples, _ = tempo_change_track()
    beatmap = generate_beatmap_from_audio(samples, 22050, target_events_per_minute=150)
    event_times = np.array([event["time_sec"] for event in beatmap["events"]], dtype=np.float32)

    first_half = event_times[(event_times >= 1.0) & (event_times < 7.5)]
    second_half = event_times[(event_times >= 8.5) & (event_times < 15.0)]

    assert len(first_half) >= 8
    assert len(second_half) >= 6
    assert abs(float(np.median(np.diff(first_half))) - 0.5) <= 0.12
    assert abs(float(np.median(np.diff(second_half))) - (60.0 / 90.0)) <= 0.16


def test_dense_noise_is_capped() -> None:
    rng = np.random.default_rng(1234)
    samples = rng.normal(0.0, 0.22, 22050 * 12).astype(np.float32)
    beatmap = generate_beatmap_from_audio(samples, 22050, target_events_per_minute=120)

    events_per_minute = len(beatmap["events"]) / (beatmap["source"]["duration_sec"] / 60.0)
    assert events_per_minute <= 130


