from __future__ import annotations

from beat_extractor.generator import generate_beatmap_from_audio
from beat_extractor.schema import validate_beatmap


def test_generated_beatmap_schema_is_valid(click_track) -> None:
    samples, _ = click_track()
    beatmap = generate_beatmap_from_audio(samples, 22050, target_events_per_minute=150)

    validate_beatmap(beatmap)


def test_events_are_sorted_stable_and_in_duration(click_track) -> None:
    samples, _ = click_track()
    beatmap = generate_beatmap_from_audio(samples, 22050, target_events_per_minute=150)

    times = [event["time_sec"] for event in beatmap["events"]]
    ids = [event["id"] for event in beatmap["events"]]

    assert times == sorted(times)
    assert ids == [f"evt_{index:06d}" for index in range(1, len(ids) + 1)]
    assert all(0.0 <= time <= beatmap["source"]["duration_sec"] for time in times)

