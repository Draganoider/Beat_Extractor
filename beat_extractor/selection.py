from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from beat_extractor.analysis import AudioFeatures, nearest_distance, value_at_time


SOURCE_PRIORITY = {
    "downbeat": 5,
    "section": 4,
    "beat": 3,
    "onset": 2,
}


@dataclass(frozen=True)
class CandidateEvent:
    time_sec: float
    source: str
    strength: float
    confidence: float
    score: float


def build_candidates(features: AudioFeatures) -> list[CandidateEvent]:
    candidates: list[CandidateEvent] = []

    downbeat_set = {round(float(t), 3) for t in features.downbeat_times}
    for time_sec in features.beat_times:
        source = "downbeat" if round(float(time_sec), 3) in downbeat_set else "beat"
        candidates.append(_candidate_from_time(float(time_sec), source, features))

    for time_sec in features.onset_times:
        candidates.append(_candidate_from_time(float(time_sec), "onset", features))

    for time_sec in features.section_times:
        candidates.append(_candidate_from_time(float(time_sec), "section", features))

    return deduplicate_candidates(candidates)


def deduplicate_candidates(
    candidates: list[CandidateEvent],
    merge_window_sec: float = 0.06,
) -> list[CandidateEvent]:
    if not candidates:
        return []

    ordered = sorted(candidates, key=lambda item: item.time_sec)
    groups: list[list[CandidateEvent]] = []
    current = [ordered[0]]
    for candidate in ordered[1:]:
        if candidate.time_sec - current[-1].time_sec <= merge_window_sec:
            current.append(candidate)
        else:
            groups.append(current)
            current = [candidate]
    groups.append(current)

    merged = [_merge_group(group) for group in groups]
    return sorted(merged, key=lambda item: item.time_sec)


def select_events(
    candidates: list[CandidateEvent],
    duration_sec: float,
    target_events_per_minute: int = 115,
    min_spacing_sec: float = 0.18,
) -> list[CandidateEvent]:
    if duration_sec <= 0.0 or not candidates:
        return []

    max_events = max(1, int(np.ceil(duration_sec / 60.0 * target_events_per_minute)))
    window_sec = 8.0
    window_cap = max(3, int(np.ceil(window_sec / 60.0 * target_events_per_minute)))
    by_score = sorted(candidates, key=lambda item: (item.score, item.strength), reverse=True)
    selected: list[CandidateEvent] = []
    window_counts: dict[int, int] = {}

    adaptive_threshold = _score_threshold(candidates)
    for candidate in by_score:
        if len(selected) >= max_events:
            break
        if candidate.score < adaptive_threshold and candidate.source not in {"downbeat", "section"}:
            continue
        if _too_close(candidate, selected, min_spacing_sec):
            continue
        window_index = int(candidate.time_sec // window_sec)
        cap = window_cap + (1 if candidate.source in {"downbeat", "section"} else 0)
        if window_counts.get(window_index, 0) >= cap:
            continue
        selected.append(candidate)
        window_counts[window_index] = window_counts.get(window_index, 0) + 1

    return sorted(selected, key=lambda item: item.time_sec)


def _candidate_from_time(time_sec: float, source: str, features: AudioFeatures) -> CandidateEvent:
    onset = value_at_time(features.onset_strength, features.frame_times, time_sec)
    rms = value_at_time(features.rms, features.frame_times, time_sec)
    low = value_at_time(features.low_energy, features.frame_times, time_sec)
    novelty = value_at_time(features.novelty, features.frame_times, time_sec)
    grid_distance = nearest_distance(features.beat_times, time_sec)
    grid_fit = float(np.exp(-((grid_distance / 0.12) ** 2))) if grid_distance < 0.4 else 0.0

    source_boost = {
        "downbeat": 0.2,
        "section": 0.16,
        "beat": 0.1,
        "onset": 0.0,
    }.get(source, 0.0)

    strength = 0.48 * onset + 0.18 * rms + 0.16 * low + 0.12 * novelty + 0.06 * grid_fit + source_boost
    strength = float(np.clip(strength, 0.0, 1.0))
    confidence = float(np.clip(0.58 * features.confidence + 0.3 * strength + 0.12 * grid_fit, 0.0, 1.0))
    score = float(
        np.clip(
            0.5 * strength
            + 0.24 * confidence
            + 0.14 * grid_fit
            + 0.08 * novelty
            + 0.04 * SOURCE_PRIORITY.get(source, 1) / 5.0,
            0.0,
            1.0,
        )
    )
    return CandidateEvent(time_sec=time_sec, source=source, strength=strength, confidence=confidence, score=score)


def _merge_group(group: list[CandidateEvent]) -> CandidateEvent:
    if len(group) == 1:
        return group[0]
    weights = np.array([max(item.score, 0.001) for item in group], dtype=np.float32)
    times = np.array([item.time_sec for item in group], dtype=np.float32)
    source = max(group, key=lambda item: SOURCE_PRIORITY.get(item.source, 0)).source
    return CandidateEvent(
        time_sec=float(np.average(times, weights=weights)),
        source=source,
        strength=float(max(item.strength for item in group)),
        confidence=float(max(item.confidence for item in group)),
        score=float(max(item.score for item in group)),
    )


def _too_close(candidate: CandidateEvent, selected: list[CandidateEvent], min_spacing_sec: float) -> bool:
    for event in selected:
        if abs(event.time_sec - candidate.time_sec) < min_spacing_sec:
            return True
    return False


def _score_threshold(candidates: list[CandidateEvent]) -> float:
    scores = np.array([item.score for item in candidates], dtype=np.float32)
    if scores.size == 0:
        return 1.0
    return float(min(0.55, max(0.26, np.percentile(scores, 35))))
