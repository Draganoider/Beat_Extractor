from __future__ import annotations

from dataclasses import dataclass, field


BEATMAP_VERSION = "beatmap-v1"


@dataclass(frozen=True)
class SourceInfo:
    filename: str
    sha256: str
    duration_sec: float


@dataclass(frozen=True)
class AnalysisInfo:
    bpm: float
    meter: str
    confidence: float


@dataclass(frozen=True)
class BeatEvent:
    id: str
    time_sec: float
    type: str
    strength: float
    confidence: float
    source: str
    edited: bool = False


@dataclass(frozen=True)
class Beatmap:
    source: SourceInfo
    analysis: AnalysisInfo
    events: list[BeatEvent]
    sections: list[dict] = field(default_factory=list)
    version: str = BEATMAP_VERSION


def beatmap_to_dict(beatmap: Beatmap) -> dict:
    return {
        "version": beatmap.version,
        "source": {
            "filename": beatmap.source.filename,
            "sha256": beatmap.source.sha256,
            "duration_sec": round(float(beatmap.source.duration_sec), 6),
        },
        "analysis": {
            "bpm": round(float(beatmap.analysis.bpm), 6),
            "meter": beatmap.analysis.meter,
            "confidence": round(float(beatmap.analysis.confidence), 6),
        },
        "events": [
            {
                "id": event.id,
                "time_sec": round(float(event.time_sec), 6),
                "type": event.type,
                "strength": round(float(event.strength), 6),
                "confidence": round(float(event.confidence), 6),
                "source": event.source,
                "edited": bool(event.edited),
            }
            for event in beatmap.events
        ],
        "sections": beatmap.sections,
    }


def event_id(index: int) -> str:
    return f"evt_{index:06d}"

