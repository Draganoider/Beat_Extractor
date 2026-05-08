from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from auto_determining.io import atomic_write_json

from beat_extractor.dataset import TrainingDataset, build_training_dataset
from beat_extractor.paths import MODEL_INDEX_PATH, MODEL_PATH, MODEL_RUNS_DIR
from beat_extractor.storage import iter_training_takes


MODEL_VERSION = "ranker-v1"
MODEL_FILENAME = "model.joblib"
METRICS_FILENAME = "metrics.json"
MANIFEST_FILENAME = "training_manifest.json"


def train_ranker_from_storage(model_path: str | Path = MODEL_PATH) -> dict:
    return train_ranker(iter_training_takes(status="approved"), model_path=model_path)


def train_ranker(takes: list[dict], *, model_path: str | Path = MODEL_PATH) -> dict:
    dataset = build_training_dataset(takes)
    payload = train_ranker_from_dataset(dataset)
    stats = {
        "rows": int(dataset.X.shape[0]),
        "positives": int(np.sum(dataset.y == 1)),
        "negatives": int(np.sum(dataset.y == 0)),
        "skipped_takes": dataset.skipped_takes,
        "train_accuracy": payload["train_accuracy"],
        "feature_names": payload["feature_names"],
    }
    model_path = Path(model_path)
    if model_path.suffix == ".joblib":
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(payload, model_path)
        stats["model_path"] = str(model_path)
        stats["run_id"] = model_path.stem
        return stats

    return save_model_run(payload, stats, takes, index_path=model_path)


def train_ranker_from_dataset(dataset: TrainingDataset) -> dict:
    if dataset.X.shape[0] == 0:
        raise ValueError("No training rows found. Approve at least one tap take first.")
    if len(set(dataset.y.tolist())) < 2:
        raise ValueError("Training needs both positive and negative candidate examples.")

    model = HistGradientBoostingClassifier(
        max_iter=80,
        learning_rate=0.08,
        min_samples_leaf=2,
        l2_regularization=0.02,
        class_weight="balanced",
        random_state=42,
    )
    model.fit(dataset.X, dataset.y)
    train_score = float(model.score(dataset.X, dataset.y))
    return {
        "version": MODEL_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "feature_names": dataset.feature_names,
        "model": model,
        "train_rows": int(dataset.X.shape[0]),
        "train_positives": int(np.sum(dataset.y == 1)),
        "train_negatives": int(np.sum(dataset.y == 0)),
        "train_accuracy": train_score,
    }


def load_ranker(model_path: str | Path = MODEL_PATH) -> dict | None:
    path = resolve_model_path(model_path)
    if not path.exists():
        return None
    return joblib.load(path)


def save_model_run(
    payload: dict,
    stats: dict,
    takes: list[dict],
    *,
    index_path: str | Path = MODEL_INDEX_PATH,
) -> dict:
    run_id = _new_run_id()
    run_dir = MODEL_RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    model_path = run_dir / MODEL_FILENAME
    metrics_path = run_dir / METRICS_FILENAME
    manifest_path = run_dir / MANIFEST_FILENAME

    joblib.dump(payload, model_path)
    metrics = {
        "run_id": run_id,
        "version": MODEL_VERSION,
        "created_at": payload["created_at"],
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
        "manifest_path": str(manifest_path),
        "rows": stats["rows"],
        "positives": stats["positives"],
        "negatives": stats["negatives"],
        "skipped_takes": stats["skipped_takes"],
        "train_accuracy": stats["train_accuracy"],
        "feature_names": stats["feature_names"],
    }
    manifest = {
        "run_id": run_id,
        "created_at": payload["created_at"],
        "approved_takes": [
            {
                "take_id": take.get("take_id"),
                "song_sha256": take.get("source", {}).get("sha256"),
                "filename": take.get("source", {}).get("filename"),
                "rating": take.get("rating"),
            }
            for take in takes
            if take.get("status") == "approved"
        ],
    }
    atomic_write_json(metrics_path, metrics)
    atomic_write_json(manifest_path, manifest)
    set_active_model(run_id, index_path=index_path)
    return metrics


def resolve_model_path(model_path: str | Path = MODEL_PATH) -> Path:
    path = Path(model_path)
    if path.suffix == ".joblib":
        return path
    pointer = load_active_model(index_path=path)
    if not pointer:
        return Path("__missing_model__.joblib")
    return Path(pointer["model_path"])


def load_active_model(index_path: str | Path = MODEL_INDEX_PATH) -> dict | None:
    path = Path(index_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def set_active_model(run_id: str, *, index_path: str | Path = MODEL_INDEX_PATH) -> dict:
    run_dir = MODEL_RUNS_DIR / run_id
    metrics_path = run_dir / METRICS_FILENAME
    model_path = run_dir / MODEL_FILENAME
    if not model_path.exists() or not metrics_path.exists():
        raise FileNotFoundError(f"Model run not found: {run_id}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    pointer = {
        "version": "active-model-v1",
        "run_id": run_id,
        "activated_at": datetime.now(UTC).isoformat(),
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
    }
    atomic_write_json(index_path, pointer)
    return {**metrics, **pointer}


def list_model_runs() -> list[dict]:
    if not MODEL_RUNS_DIR.exists():
        return []
    runs = []
    active = load_active_model()
    active_run_id = active.get("run_id") if active else None
    for metrics_path in sorted(MODEL_RUNS_DIR.glob(f"*/{METRICS_FILENAME}"), reverse=True):
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        metrics["active"] = metrics.get("run_id") == active_run_id
        runs.append(metrics)
    return runs


def _new_run_id() -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{MODEL_VERSION}_{uuid.uuid4().hex[:8]}"
