from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from beat_extractor.dataset import TrainingDataset, build_training_dataset
from beat_extractor.paths import MODEL_PATH
from beat_extractor.storage import iter_training_takes


MODEL_VERSION = "ranker-v1"


def train_ranker_from_storage(model_path: str | Path = MODEL_PATH) -> dict:
    return train_ranker(iter_training_takes(status="approved"), model_path=model_path)


def train_ranker(takes: list[dict], *, model_path: str | Path = MODEL_PATH) -> dict:
    dataset = build_training_dataset(takes)
    payload = train_ranker_from_dataset(dataset)
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, model_path)
    return {
        "model_path": str(model_path),
        "rows": int(dataset.X.shape[0]),
        "positives": int(np.sum(dataset.y == 1)),
        "negatives": int(np.sum(dataset.y == 0)),
        "skipped_takes": dataset.skipped_takes,
    }


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
    path = Path(model_path)
    if not path.exists():
        return None
    return joblib.load(path)

