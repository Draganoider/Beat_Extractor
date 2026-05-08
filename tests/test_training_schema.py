from __future__ import annotations

from beat_extractor.training_schema import validate_training_take


def test_valid_training_take_schema() -> None:
    take = {
        "version": "training-take-v1",
        "take_id": "take_1",
        "created_at": "2026-01-01T00:00:00Z",
        "user_id": "local_user",
        "style": "normal",
        "status": "approved",
        "rating": 5,
        "notes": "",
        "source": {
            "filename": "song.wav",
            "path": "song.wav",
            "sha256": "abc",
            "duration_sec": 3.0,
        },
        "calibration": {
            "spacebar_latency_ms": 75.0,
            "mouse_latency_ms": 110.0,
        },
        "raw_taps": [{"time_sec": 1.075, "input_kind": "spacebar"}],
        "cleaned_events": [{"time_sec": 1.0, "type": "hit"}],
    }

    validate_training_take(take)

