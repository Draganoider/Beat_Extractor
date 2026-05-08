from __future__ import annotations

import json

import soundfile as sf

from auto_determining.io import atomic_write_json

from beat_extractor.contributions import export_contribution_bundle, import_contribution_bundle
from beat_extractor.storage import build_training_take


def test_export_and_import_contribution_bundle(tmp_path, monkeypatch, click_track) -> None:
    from beat_extractor import contributions, storage

    source_takes = tmp_path / "source" / "takes"
    imported_takes = tmp_path / "imported" / "takes"
    imported_uploads = tmp_path / "imported" / "uploads"
    source_takes.mkdir(parents=True)
    imported_takes.mkdir(parents=True)
    imported_uploads.mkdir(parents=True)

    samples, expected_times = click_track(duration=6.0)
    audio_path = tmp_path / "song.wav"
    sf.write(audio_path, samples, 22050)
    take = build_training_take(
        audio_path,
        raw_taps=[{"time_sec": float(time_sec), "input_kind": "spacebar"} for time_sec in expected_times[:4]],
        cleaned_events=[{"time_sec": float(time_sec), "type": "hit"} for time_sec in expected_times[:4]],
        calibration={"spacebar_latency_ms": 0.0, "mouse_latency_ms": 0.0},
        rating=5,
        notes="",
        status="approved",
    )
    take_path = source_takes / take["source"]["sha256"][:16] / f"{take['take_id']}.training.json"
    atomic_write_json(take_path, take)

    monkeypatch.setattr(storage, "TAKES_DIR", source_takes)
    bundle_path = export_contribution_bundle(contributor_id="alex", output_path=tmp_path / "alex.contribution.zip")

    monkeypatch.setattr(contributions, "TAKES_DIR", imported_takes)
    monkeypatch.setattr(contributions, "UPLOAD_DIR", imported_uploads)
    stats = import_contribution_bundle(bundle_path)

    imported_take_files = list(imported_takes.glob("*/*.training.json"))
    imported_audio_files = list(imported_uploads.glob("*.wav"))
    imported_take = json.loads(imported_take_files[0].read_text(encoding="utf-8"))

    assert stats["imported_takes"] == 1
    assert len(imported_take_files) == 1
    assert len(imported_audio_files) == 1
    assert imported_take["source"]["path"] == str(imported_audio_files[0])

