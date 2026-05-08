from __future__ import annotations

from pathlib import Path

import numpy as np

from auto_determining.generator import generate_beatmap
from auto_determining.io import sha256_file
from auto_determining.models import AnalysisInfo, BeatEvent, Beatmap, SourceInfo, beatmap_to_dict, event_id
from auto_determining.schema import validate_beatmap
from auto_determining.selection import CandidateEvent, select_events

from beat_extractor.features import extract_candidate_feature_set, rows_to_matrix
from beat_extractor.ml import load_ranker
from beat_extractor.paths import MODEL_PATH


def generate_ai_beatmap(
    audio_path: str | Path,
    *,
    model_path: str | Path = MODEL_PATH,
    target_events_per_minute: int = 115,
    min_spacing_sec: float = 0.18,
) -> dict:
    model_payload = load_ranker(model_path)
    if model_payload is None:
        beatmap = generate_beatmap(
            audio_path,
            target_events_per_minute=target_events_per_minute,
            min_spacing_sec=min_spacing_sec,
        )
        beatmap["generator"] = "auto_determining_fallback"
        return beatmap

    path = Path(audio_path)
    feature_set = extract_candidate_feature_set(path)
    X = rows_to_matrix(feature_set.rows, model_payload["feature_names"])
    probabilities = model_payload["model"].predict_proba(X)[:, 1] if X.size else np.array([], dtype=np.float32)
    scored = []
    for candidate, probability in zip(feature_set.candidates, probabilities):
        probability = float(probability)
        scored.append(
            CandidateEvent(
                time_sec=candidate.time_sec,
                source=candidate.source,
                strength=float(max(candidate.strength, probability)),
                confidence=probability,
                score=probability,
            )
        )
    selected = select_events(
        scored,
        duration_sec=feature_set.audio.duration_sec,
        target_events_per_minute=target_events_per_minute,
        min_spacing_sec=min_spacing_sec,
    )
    beatmap = _beatmap_from_candidates(
        path,
        selected,
        duration_sec=feature_set.audio.duration_sec,
        bpm=float(feature_set.features.bpm),
        analysis_confidence=float(feature_set.features.confidence),
    )
    beatmap["generator"] = "ml_ranker_v1"
    return beatmap


def beatmap_from_cleaned_events(audio_path: str | Path, cleaned_events: list[dict]) -> dict:
    path = Path(audio_path)
    from auto_determining.audio import load_audio

    audio = load_audio(path)
    candidates = [
        CandidateEvent(
            time_sec=float(event["time_sec"]),
            source="onset",
            strength=1.0,
            confidence=1.0,
            score=1.0,
        )
        for event in cleaned_events
    ]
    beatmap = _beatmap_from_candidates(path, candidates, duration_sec=audio.duration_sec, bpm=0.0, analysis_confidence=1.0)
    beatmap["generator"] = "human_taps"
    return beatmap


def _beatmap_from_candidates(
    path: Path,
    candidates: list[CandidateEvent],
    *,
    duration_sec: float,
    bpm: float,
    analysis_confidence: float,
) -> dict:
    events = [
        BeatEvent(
            id=event_id(index + 1),
            time_sec=max(0.0, min(float(candidate.time_sec), duration_sec)),
            type="hit",
            strength=float(candidate.strength),
            confidence=float(candidate.confidence),
            source=candidate.source,
            edited=False,
        )
        for index, candidate in enumerate(sorted(candidates, key=lambda item: item.time_sec))
    ]
    payload = beatmap_to_dict(
        Beatmap(
            source=SourceInfo(filename=path.name, sha256=sha256_file(path), duration_sec=duration_sec),
            analysis=AnalysisInfo(bpm=bpm, meter="4/4", confidence=analysis_confidence),
            events=events,
            sections=[],
        )
    )
    validate_beatmap(payload)
    return payload

