from __future__ import annotations


def validate_training_take(take: dict) -> None:
    _require(isinstance(take, dict), "Training take must be an object.")
    _require(take.get("version") == "training-take-v1", "Unsupported training take version.")
    _require(take.get("user_id") == "local_user", "Only local_user is supported in v1.")
    _require(take.get("style") == "normal", "Only normal style is supported in v1.")
    _require(take.get("status") in {"draft", "approved", "rejected"}, "Invalid take status.")
    _number(take.get("rating"), "rating")

    source = take.get("source")
    _require(isinstance(source, dict), "Missing source.")
    _require(isinstance(source.get("path"), str) and source["path"], "Missing source path.")
    _require(isinstance(source.get("sha256"), str) and source["sha256"], "Missing source hash.")
    duration = _number(source.get("duration_sec"), "source.duration_sec")
    _require(duration >= 0.0, "Duration must be non-negative.")

    calibration = take.get("calibration")
    _require(isinstance(calibration, dict), "Missing calibration.")
    for key in ("spacebar_latency_ms", "mouse_latency_ms"):
        _require(calibration.get(key) is not None, f"Missing {key}.")
        _number(calibration.get(key), key)

    _validate_taps(take.get("raw_taps"), duration, allow_input_kind=True, name="raw_taps")
    _validate_taps(take.get("cleaned_events"), duration, allow_input_kind=False, name="cleaned_events")


def _validate_taps(items, duration: float, *, allow_input_kind: bool, name: str) -> None:
    _require(isinstance(items, list), f"{name} must be a list.")
    previous = -1.0
    for item in items:
        _require(isinstance(item, dict), f"{name} item must be an object.")
        time_sec = _number(item.get("time_sec"), f"{name}.time_sec")
        _require(0.0 <= time_sec <= duration + 1e-6, f"{name} time outside duration.")
        _require(time_sec >= previous, f"{name} must be sorted.")
        if allow_input_kind:
            _require(item.get("input_kind") in {"spacebar", "mouse"}, "Unsupported input kind.")
        else:
            _require(item.get("type") == "hit", "Cleaned events must be hits.")
        previous = time_sec


def _number(value, name: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{name} must be a number.")
    return float(value)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

