from __future__ import annotations

import soundfile as sf

from auto_determining.schema import validate_beatmap

from beat_extractor.ai_generator import generate_ai_beatmap
from beat_extractor.ml import train_ranker
from beat_extractor.storage import build_training_take


def test_ai_generation_falls_back_without_model(tmp_path, click_track) -> None:
    samples, _ = click_track(duration=6.0)
    audio_path = tmp_path / "click.wav"
    sf.write(audio_path, samples, 22050)

    beatmap = generate_ai_beatmap(audio_path, model_path=tmp_path / "missing.joblib")

    validate_beatmap(beatmap)
    assert beatmap["generator"] == "auto_determining_fallback"


def test_ai_generation_with_trained_model(tmp_path, click_track) -> None:
    samples, expected_times = click_track(duration=8.0)
    audio_path = tmp_path / "click.wav"
    model_path = tmp_path / "model.joblib"
    sf.write(audio_path, samples, 22050)
    selected_times = [float(time_sec) for index, time_sec in enumerate(expected_times) if index % 2 == 0]
    take = build_training_take(
        audio_path,
        raw_taps=[{"time_sec": time_sec, "input_kind": "spacebar"} for time_sec in selected_times],
        cleaned_events=[{"time_sec": time_sec, "type": "hit"} for time_sec in selected_times],
        calibration={"spacebar_latency_ms": 0.0, "mouse_latency_ms": 0.0},
        rating=5,
        notes="",
        status="approved",
    )
    train_ranker([take], model_path=model_path)

    beatmap = generate_ai_beatmap(audio_path, model_path=model_path)

    validate_beatmap(beatmap)
    assert beatmap["generator"] == "ml_ranker_v1"
    assert len(beatmap["events"]) > 0

