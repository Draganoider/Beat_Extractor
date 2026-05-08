from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture
def click_track(sample_rate: int = 22050, duration: float = 8.0, bpm: float = 120.0) -> tuple[np.ndarray, np.ndarray]:
    def build(sample_rate: int = sample_rate, duration: float = duration, bpm: float = bpm) -> tuple[np.ndarray, np.ndarray]:
        samples = np.zeros(int(sample_rate * duration), dtype=np.float32)
        interval = 60.0 / bpm
        times = np.arange(0.5, duration - 0.1, interval, dtype=np.float32)
        click_len = int(sample_rate * 0.025)
        envelope = np.exp(-np.linspace(0.0, 8.0, click_len)).astype(np.float32)
        tone = np.sin(2.0 * np.pi * 1600.0 * np.arange(click_len) / sample_rate).astype(np.float32)
        click = envelope * tone
        for time_sec in times:
            start = int(time_sec * sample_rate)
            end = min(start + click_len, len(samples))
            samples[start:end] += click[: end - start]
        return samples, times

    return build


@pytest.fixture
def tempo_change_track(sample_rate: int = 22050) -> tuple[np.ndarray, np.ndarray]:
    def build(sample_rate: int = sample_rate) -> tuple[np.ndarray, np.ndarray]:
        duration = 16.0
        samples = np.zeros(int(sample_rate * duration), dtype=np.float32)
        first = np.arange(0.5, 8.0, 0.5, dtype=np.float32)
        second = np.arange(8.0, duration - 0.1, 60.0 / 90.0, dtype=np.float32)
        times = np.concatenate([first, second])
        click_len = int(sample_rate * 0.025)
        envelope = np.exp(-np.linspace(0.0, 8.0, click_len)).astype(np.float32)
        tone = np.sin(2.0 * np.pi * 1400.0 * np.arange(click_len) / sample_rate).astype(np.float32)
        click = envelope * tone
        for time_sec in times:
            start = int(time_sec * sample_rate)
            end = min(start + click_len, len(samples))
            samples[start:end] += click[: end - start]
        return samples, times

    return build
