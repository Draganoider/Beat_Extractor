from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from auto_determining.analysis import extract_features, nearest_distance, value_at_time
from auto_determining.audio import AudioData, load_audio
from auto_determining.selection import SOURCE_PRIORITY, CandidateEvent, build_candidates


FEATURE_NAMES = [
    "candidate_strength",
    "candidate_confidence",
    "candidate_score",
    "source_priority",
    "onset_strength",
    "rms",
    "low_energy",
    "novelty",
    "beat_distance",
    "downbeat_distance",
    "section_distance",
    "beat_fit",
    "time_norm",
    "local_density_1s",
]


@dataclass(frozen=True)
class CandidateFeatureSet:
    audio: AudioData
    features: object
    candidates: list[CandidateEvent]
    rows: list[dict]


def extract_candidate_feature_set(audio_path: str | Path) -> CandidateFeatureSet:
    audio = load_audio(audio_path)
    features = extract_features(audio)
    candidates = build_candidates(features)
    rows = _feature_rows(candidates, features, audio.duration_sec)
    return CandidateFeatureSet(audio=audio, features=features, candidates=candidates, rows=rows)


def rows_to_matrix(rows: list[dict], feature_names: list[str] | None = None) -> np.ndarray:
    feature_names = feature_names or FEATURE_NAMES
    matrix = [[float(row.get(name, 0.0)) for name in feature_names] for row in rows]
    return np.asarray(matrix, dtype=np.float32)


def _feature_rows(candidates: list[CandidateEvent], features, duration_sec: float) -> list[dict]:
    times = np.asarray([candidate.time_sec for candidate in candidates], dtype=np.float32)
    rows = []
    for candidate in candidates:
        time_sec = float(candidate.time_sec)
        beat_distance = min(nearest_distance(features.beat_times, time_sec), 2.0)
        downbeat_distance = min(nearest_distance(features.downbeat_times, time_sec), 4.0)
        section_distance = min(nearest_distance(features.section_times, time_sec), 8.0)
        beat_fit = float(np.exp(-((beat_distance / 0.12) ** 2))) if beat_distance < 0.4 else 0.0
        local_density = int(np.sum(np.abs(times - time_sec) <= 0.5)) if times.size else 0
        rows.append(
            {
                "time_sec": time_sec,
                "source": candidate.source,
                "candidate_strength": float(candidate.strength),
                "candidate_confidence": float(candidate.confidence),
                "candidate_score": float(candidate.score),
                "source_priority": SOURCE_PRIORITY.get(candidate.source, 1) / 5.0,
                "onset_strength": value_at_time(features.onset_strength, features.frame_times, time_sec),
                "rms": value_at_time(features.rms, features.frame_times, time_sec),
                "low_energy": value_at_time(features.low_energy, features.frame_times, time_sec),
                "novelty": value_at_time(features.novelty, features.frame_times, time_sec),
                "beat_distance": beat_distance,
                "downbeat_distance": downbeat_distance,
                "section_distance": section_distance,
                "beat_fit": beat_fit,
                "time_norm": time_sec / max(duration_sec, 1e-6),
                "local_density_1s": local_density,
            }
        )
    return rows

