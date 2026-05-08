from __future__ import annotations

import soundfile as sf

from beat_extractor.ml import load_ranker, train_ranker
from beat_extractor.storage import build_training_take


def test_train_ranker_from_approved_take(tmp_path, click_track) -> None:
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

    stats = train_ranker([take], model_path=model_path)
    payload = load_ranker(model_path)

    assert model_path.exists()
    assert stats["positives"] > 0
    assert stats["negatives"] > 0
    assert payload["version"] == "ranker-v1"

