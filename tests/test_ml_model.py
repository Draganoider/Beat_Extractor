from __future__ import annotations

import soundfile as sf

from beat_extractor.ml import list_model_runs, load_active_model, load_ranker, set_active_model, train_ranker
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


def test_train_ranker_saves_versioned_run_and_active_pointer(tmp_path, monkeypatch, click_track) -> None:
    from beat_extractor import ml

    monkeypatch.setattr(ml, "MODEL_RUNS_DIR", tmp_path / "runs")
    samples, expected_times = click_track(duration=8.0)
    audio_path = tmp_path / "click.wav"
    index_path = tmp_path / "current_model.json"
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

    stats = train_ranker([take], model_path=index_path)
    active = load_active_model(index_path)
    payload = load_ranker(index_path)

    assert active["run_id"] == stats["run_id"]
    assert payload["version"] == "ranker-v1"
    assert (tmp_path / "runs" / stats["run_id"] / "metrics.json").exists()
    assert (tmp_path / "runs" / stats["run_id"] / "training_manifest.json").exists()


def test_activate_previous_model_run(tmp_path, monkeypatch, click_track) -> None:
    from beat_extractor import ml

    monkeypatch.setattr(ml, "MODEL_RUNS_DIR", tmp_path / "runs")
    samples, expected_times = click_track(duration=8.0)
    audio_path = tmp_path / "click.wav"
    index_path = tmp_path / "current_model.json"
    sf.write(audio_path, samples, 22050)
    take = build_training_take(
        audio_path,
        raw_taps=[{"time_sec": float(time_sec), "input_kind": "spacebar"} for time_sec in expected_times[::2]],
        cleaned_events=[{"time_sec": float(time_sec), "type": "hit"} for time_sec in expected_times[::2]],
        calibration={"spacebar_latency_ms": 0.0, "mouse_latency_ms": 0.0},
        rating=5,
        notes="",
        status="approved",
    )
    first = train_ranker([take], model_path=index_path)
    second = train_ranker([take], model_path=index_path)

    activated = set_active_model(first["run_id"], index_path=index_path)

    assert first["run_id"] != second["run_id"]
    assert activated["run_id"] == first["run_id"]
