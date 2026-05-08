from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class AudioData:
    samples: np.ndarray
    sample_rate: int

    @property
    def duration_sec(self) -> float:
        if self.sample_rate <= 0:
            return 0.0
        return float(len(self.samples) / self.sample_rate)


def load_audio(path: str | Path, sample_rate: int = 22050) -> AudioData:
    path = Path(path)
    try:
        import librosa

        samples, actual_rate = librosa.load(path, sr=sample_rate, mono=True)
        return AudioData(_clean_samples(samples), int(actual_rate))
    except Exception as librosa_error:
        try:
            return _load_audio_ffmpeg(path, sample_rate)
        except Exception as ffmpeg_error:
            raise RuntimeError(
                f"Could not decode audio with librosa or FFmpeg: {path}"
            ) from ffmpeg_error or librosa_error


def audio_from_samples(samples: np.ndarray, sample_rate: int) -> AudioData:
    return AudioData(_clean_samples(samples), int(sample_rate))


def _clean_samples(samples: np.ndarray) -> np.ndarray:
    cleaned = np.asarray(samples, dtype=np.float32).reshape(-1)
    if cleaned.size == 0:
        return cleaned
    cleaned = np.nan_to_num(cleaned, nan=0.0, posinf=0.0, neginf=0.0)
    cleaned = cleaned - float(np.mean(cleaned))
    peak = float(np.max(np.abs(cleaned)))
    if peak > 1.0:
        cleaned = cleaned / peak
    return cleaned.astype(np.float32, copy=False)


def _load_audio_ffmpeg(path: Path, sample_rate: int) -> AudioData:
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-",
    ]
    result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    samples = np.frombuffer(result.stdout, dtype=np.float32).copy()
    return AudioData(_clean_samples(samples), sample_rate)

