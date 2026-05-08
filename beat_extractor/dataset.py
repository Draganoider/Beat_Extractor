from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from beat_extractor.features import FEATURE_NAMES, extract_candidate_feature_set, rows_to_matrix


LABEL_TOLERANCE_SEC = 0.08


@dataclass(frozen=True)
class TrainingDataset:
    X: np.ndarray
    y: np.ndarray
    rows: list[dict]
    feature_names: list[str]
    skipped_takes: int = 0


def build_training_dataset(takes: list[dict], *, label_tolerance_sec: float = LABEL_TOLERANCE_SEC) -> TrainingDataset:
    all_rows: list[dict] = []
    all_labels: list[int] = []
    skipped = 0

    for take in takes:
        if take.get("status") != "approved":
            continue
        audio_path = Path(take["source"]["path"])
        if not audio_path.exists():
            skipped += 1
            continue
        feature_set = extract_candidate_feature_set(audio_path)
        human_times = [float(event["time_sec"]) for event in take.get("cleaned_events", [])]
        labels = label_candidate_rows(feature_set.rows, human_times, tolerance_sec=label_tolerance_sec)
        for row, label in zip(feature_set.rows, labels):
            enriched = dict(row)
            enriched["song_sha256"] = take["source"]["sha256"]
            enriched["take_id"] = take["take_id"]
            all_rows.append(enriched)
            all_labels.append(label)

    X = rows_to_matrix(all_rows, FEATURE_NAMES) if all_rows else np.zeros((0, len(FEATURE_NAMES)), dtype=np.float32)
    y = np.asarray(all_labels, dtype=np.int8)
    return TrainingDataset(X=X, y=y, rows=all_rows, feature_names=list(FEATURE_NAMES), skipped_takes=skipped)


def label_candidate_rows(rows: list[dict], human_times: list[float], *, tolerance_sec: float = LABEL_TOLERANCE_SEC) -> list[int]:
    if not human_times:
        return [0 for _ in rows]
    human = np.asarray(sorted(human_times), dtype=np.float32)
    labels = []
    for row in rows:
        time_sec = float(row["time_sec"])
        index = int(np.searchsorted(human, time_sec))
        distances = []
        if index < human.size:
            distances.append(abs(float(human[index]) - time_sec))
        if index > 0:
            distances.append(abs(float(human[index - 1]) - time_sec))
        labels.append(1 if distances and min(distances) <= tolerance_sec else 0)
    return labels

