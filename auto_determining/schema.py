from __future__ import annotations


ALLOWED_SOURCES = {"beat", "onset", "downbeat", "section"}
ALLOWED_EVENT_TYPES = {"hit"}


def validate_beatmap(beatmap: dict) -> None:
    _require(isinstance(beatmap, dict), "Beatmap must be an object.")
    _require(beatmap.get("version") == "beatmap-v1", "Unsupported beatmap version.")

    source = beatmap.get("source")
    _require(isinstance(source, dict), "Missing source object.")
    _require(isinstance(source.get("filename"), str) and source["filename"], "Missing source filename.")
    _require(isinstance(source.get("sha256"), str) and source["sha256"], "Missing source hash.")
    duration = _number(source.get("duration_sec"), "source.duration_sec")
    _require(duration >= 0.0, "Duration must be non-negative.")

    analysis = beatmap.get("analysis")
    _require(isinstance(analysis, dict), "Missing analysis object.")
    _number(analysis.get("bpm"), "analysis.bpm")
    _require(isinstance(analysis.get("meter"), str) and analysis["meter"], "Missing meter.")
    confidence = _number(analysis.get("confidence"), "analysis.confidence")
    _require(0.0 <= confidence <= 1.0, "Analysis confidence must be between 0 and 1.")

    events = beatmap.get("events")
    _require(isinstance(events, list), "Events must be a list.")
    previous_time = -1.0
    seen_ids: set[str] = set()
    for event in events:
        _validate_event(event, duration)
        _require(event["id"] not in seen_ids, f"Duplicate event id: {event['id']}")
        _require(event["time_sec"] >= previous_time, "Events must be sorted by time.")
        seen_ids.add(event["id"])
        previous_time = event["time_sec"]

    sections = beatmap.get("sections")
    _require(isinstance(sections, list), "Sections must be a list.")


def _validate_event(event: dict, duration: float) -> None:
    _require(isinstance(event, dict), "Event must be an object.")
    _require(isinstance(event.get("id"), str) and event["id"].startswith("evt_"), "Invalid event id.")
    time_sec = _number(event.get("time_sec"), "event.time_sec")
    _require(0.0 <= time_sec <= duration + 1e-6, "Event time outside song duration.")
    _require(event.get("type") in ALLOWED_EVENT_TYPES, "Unsupported event type.")
    strength = _number(event.get("strength"), "event.strength")
    confidence = _number(event.get("confidence"), "event.confidence")
    _require(0.0 <= strength <= 1.0, "Event strength must be between 0 and 1.")
    _require(0.0 <= confidence <= 1.0, "Event confidence must be between 0 and 1.")
    _require(event.get("source") in ALLOWED_SOURCES, "Unsupported event source.")
    _require(isinstance(event.get("edited"), bool), "Event edited flag must be boolean.")


def _number(value, name: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{name} must be a number.")
    return float(value)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


