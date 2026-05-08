from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
BEATMAP_DIR = DATA_DIR / "beatmaps"
TMP_DIR = DATA_DIR / "tmp"
TRAINING_DIR = DATA_DIR / "training"
PROFILE_DIR = TRAINING_DIR / "profiles"
TAKES_DIR = TRAINING_DIR / "takes"
MODELS_DIR = DATA_DIR / "models"
MODEL_RUNS_DIR = MODELS_DIR / "runs"
MODEL_INDEX_PATH = MODELS_DIR / "current_model.json"
MODEL_PATH = MODEL_INDEX_PATH
USER_ID = "local_user"


def ensure_data_dirs() -> None:
    for path in (UPLOAD_DIR, BEATMAP_DIR, TMP_DIR, TRAINING_DIR, PROFILE_DIR, TAKES_DIR, MODELS_DIR, MODEL_RUNS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def profile_path(user_id: str = USER_ID) -> Path:
    return PROFILE_DIR / f"{user_id}.json"
