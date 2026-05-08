from __future__ import annotations

import numpy as np

from beat_extractor.generator import generate_beatmap_from_audio
from beat_extractor.selection import CandidateEvent, deduplicate_candidates, select_events


def test_deduplication_merges_near_identical_candidates() -> None:
    candidates = [
        CandidateEvent(1.000, "onset", 0.5, 0.5, 0.5),
        CandidateEvent(1.030, "downbeat", 0.8, 0.7, 0.75),
        CandidateEvent(1.200, "beat", 0.3, 0.4, 0.35),
    ]

    merged = deduplicate_candidates(candidates, merge_window_sec=0.06)

    assert len(merged) == 2
    assert merged[0].source == "downbeat"
    assert merged[0].strength == 0.8


def test_density_rules_enforce_minimum_spacing() -> None:
    candidates = [
        CandidateEvent(index * 0.05, "onset", 0.9, 0.9, 0.9)
        for index in range(40)
    ]

    selected = select_events(candidates, duration_sec=3.0, target_events_per_minute=180, min_spacing_sec=0.18)
    times = [event.time_sec for event in selected]

    assert all((right - left) >= 0.18 for left, right in zip(times, times[1:]))


def test_confidence_is_lower_for_ambiguous_audio(click_track) -> None:
    click_samples, _ = click_track()
    strong = generate_beatmap_from_audio(click_samples, 22050, target_events_per_minute=150)

    t = np.arange(22050 * 8, dtype=np.float32) / 22050.0
    sine = (0.12 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
    weak = generate_beatmap_from_audio(sine, 22050, target_events_per_minute=150)

    assert strong["analysis"]["confidence"] > weak["analysis"]["confidence"]

