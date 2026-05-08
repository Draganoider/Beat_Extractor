from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from beat_extractor.audio import load_audio


def render_click_preview(
    audio_path: str | Path,
    beatmap: dict,
    output_path: str | Path,
    *,
    sample_rate: int = 44100,
    click_gain: float = 0.45,
) -> Path:
    audio = load_audio(audio_path, sample_rate=sample_rate)
    mix = np.array(audio.samples, dtype=np.float32, copy=True) * 0.82
    click = _make_click(sample_rate)

    for event in beatmap.get("events", []):
        time_sec = float(event.get("time_sec", -1.0))
        if time_sec < 0.0:
            continue
        start = int(round(time_sec * sample_rate))
        if start >= mix.size:
            continue
        end = min(mix.size, start + click.size)
        strength = float(event.get("strength", 0.75))
        gain = click_gain * (0.45 + 0.55 * np.clip(strength, 0.0, 1.0))
        mix[start:end] += gain * click[: end - start]

    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0.98:
        mix = mix / peak * 0.98

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output, mix, sample_rate, subtype="PCM_16")
    return output


def _make_click(sample_rate: int) -> np.ndarray:
    duration_sec = 0.055
    t = np.arange(int(sample_rate * duration_sec), dtype=np.float32) / sample_rate
    tone = np.sin(2.0 * np.pi * 2200.0 * t) + 0.45 * np.sin(2.0 * np.pi * 3300.0 * t)
    envelope = np.exp(-95.0 * t)
    click = tone * envelope
    peak = float(np.max(np.abs(click))) if click.size else 1.0
    return (click / max(peak, 1e-6)).astype(np.float32)

