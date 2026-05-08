from __future__ import annotations

from pathlib import Path

import numpy as np

from beat_extractor.analysis import extract_features
from beat_extractor.audio import audio_from_samples, load_audio
from beat_extractor.io import sha256_file
from beat_extractor.models import AnalysisInfo, BeatEvent, Beatmap, SourceInfo, beatmap_to_dict, event_id
from beat_extractor.schema import validate_beatmap
from beat_extractor.selection import build_candidates, select_events


def generate_beatmap(
    audio_path: str | Path,
    *,
    target_events_per_minute: int = 115,
    min_spacing_sec: float = 0.18,
) -> dict:
    path = Path(audio_path)
    audio = load_audio(path)
    return _generate(
        audio.samples,
        audio.sample_rate,
        source_filename=path.name,
        source_sha256=sha256_file(path),
        target_events_per_minute=target_events_per_minute,
        min_spacing_sec=min_spacing_sec,
    )


def generate_beatmap_from_audio(
    samples: np.ndarray,
    sample_rate: int,
    *,
    source_filename: str = "synthetic.wav",
    source_sha256: str = "synthetic",
    target_events_per_minute: int = 115,
    min_spacing_sec: float = 0.18,
) -> dict:
    audio = audio_from_samples(samples, sample_rate)
    return _generate(
        audio.samples,
        audio.sample_rate,
        source_filename=source_filename,
        source_sha256=source_sha256,
        target_events_per_minute=target_events_per_minute,
        min_spacing_sec=min_spacing_sec,
    )


def _generate(
    samples: np.ndarray,
    sample_rate: int,
    *,
    source_filename: str,
    source_sha256: str,
    target_events_per_minute: int,
    min_spacing_sec: float,
) -> dict:
    audio = audio_from_samples(samples, sample_rate)
    features = extract_features(audio)
    candidates = build_candidates(features)
    selected = select_events(
        candidates,
        duration_sec=audio.duration_sec,
        target_events_per_minute=target_events_per_minute,
        min_spacing_sec=min_spacing_sec,
    )

    events = [
        BeatEvent(
            id=event_id(index + 1),
            time_sec=max(0.0, min(float(candidate.time_sec), audio.duration_sec)),
            type="hit",
            strength=float(candidate.strength),
            confidence=float(candidate.confidence),
            source=candidate.source,
            edited=False,
        )
        for index, candidate in enumerate(selected)
    ]
    beatmap = Beatmap(
        source=SourceInfo(
            filename=source_filename,
            sha256=source_sha256,
            duration_sec=audio.duration_sec,
        ),
        analysis=AnalysisInfo(
            bpm=float(features.bpm),
            meter="4/4",
            confidence=float(features.confidence),
        ),
        events=events,
        sections=[{"time_sec": round(float(t), 6), "type": "section"} for t in features.section_times],
    )
    payload = beatmap_to_dict(beatmap)
    validate_beatmap(payload)
    return payload

