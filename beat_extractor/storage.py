from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from auto_determining.audio import load_audio
from auto_determining.io import atomic_write_json, sha256_file

from beat_extractor.paths import TAKES_DIR, USER_ID, profile_path
from beat_extractor.training_schema import validate_training_take


def load_profile(user_id: str = USER_ID) -> dict:
    path = profile_path(user_id)
    if not path.exists():
        return {
            "version": "profile-v1",
            "user_id": user_id,
            "calibration": {
                "spacebar_latency_ms": None,
                "mouse_latency_ms": None,
            },
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_profile(profile: dict) -> Path:
    path = profile_path(profile.get("user_id", USER_ID))
    atomic_write_json(path, profile)
    return path


def build_training_take(
    audio_path: str | Path,
    *,
    raw_taps: list[dict],
    cleaned_events: list[dict],
    calibration: dict,
    rating: int,
    notes: str,
    status: str,
    user_id: str = USER_ID,
) -> dict:
    path = Path(audio_path)
    audio = load_audio(path)
    take = {
        "version": "training-take-v1",
        "take_id": f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}",
        "created_at": datetime.now(UTC).isoformat(),
        "user_id": user_id,
        "style": "normal",
        "status": status,
        "rating": int(rating),
        "notes": notes,
        "source": {
            "filename": path.name,
            "path": str(path),
            "sha256": sha256_file(path),
            "duration_sec": audio.duration_sec,
        },
        "calibration": {
            "spacebar_latency_ms": float(calibration["spacebar_latency_ms"]),
            "mouse_latency_ms": float(calibration["mouse_latency_ms"]),
        },
        "raw_taps": raw_taps,
        "cleaned_events": cleaned_events,
    }
    validate_training_take(take)
    return take


def save_training_take(take: dict) -> Path:
    validate_training_take(take)
    song_dir = TAKES_DIR / take["source"]["sha256"][:16]
    path = song_dir / f"{take['take_id']}.training.json"
    atomic_write_json(path, take)
    return path


def iter_training_takes(status: str | None = None) -> list[dict]:
    takes = []
    if not TAKES_DIR.exists():
        return takes
    for path in sorted(TAKES_DIR.glob("*/*.training.json")):
        take = json.loads(path.read_text(encoding="utf-8"))
        if status is None or take.get("status") == status:
            takes.append(take)
    return takes

