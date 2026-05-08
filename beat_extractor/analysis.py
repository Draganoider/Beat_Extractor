from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks

from beat_extractor.audio import AudioData


HOP_LENGTH = 512
FRAME_LENGTH = 2048


@dataclass(frozen=True)
class AudioFeatures:
    bpm: float
    beat_times: np.ndarray
    downbeat_times: np.ndarray
    onset_times: np.ndarray
    section_times: np.ndarray
    frame_times: np.ndarray
    onset_strength: np.ndarray
    rms: np.ndarray
    low_energy: np.ndarray
    novelty: np.ndarray
    confidence: float


def extract_features(audio: AudioData) -> AudioFeatures:
    import librosa

    samples = audio.samples
    sr = audio.sample_rate
    empty = np.array([], dtype=np.float32)
    duration = audio.duration_sec

    if duration <= 0.0 or _is_silence(samples):
        return AudioFeatures(0.0, empty, empty, empty, empty, empty, empty, empty, empty, empty, 0.0)

    harmonic, percussive = librosa.effects.hpss(samples)
    onset_full = librosa.onset.onset_strength(
        y=samples,
        sr=sr,
        hop_length=HOP_LENGTH,
        aggregate=np.median,
    )
    onset_percussive = librosa.onset.onset_strength(
        y=percussive,
        sr=sr,
        hop_length=HOP_LENGTH,
        aggregate=np.median,
    )
    onset_strength = 0.55 * _normalize(onset_full) + 0.45 * _normalize(onset_percussive)
    frame_times = librosa.frames_to_time(np.arange(len(onset_strength)), sr=sr, hop_length=HOP_LENGTH)

    rms = librosa.feature.rms(y=samples, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0]
    rms = _fit_length(_normalize(rms), len(onset_strength))

    low_energy = _low_frequency_energy(samples, sr, len(onset_strength))
    novelty = _section_novelty(samples, sr, len(onset_strength))

    bpm, beat_times = _track_beats(onset_strength, sr)
    onset_times = _pick_onsets(onset_strength, frame_times, duration)
    section_times = _pick_sections(novelty, frame_times, duration)
    downbeat_times = _infer_downbeats(beat_times, onset_strength, low_energy, frame_times)

    confidence = _analysis_confidence(samples, onset_strength, beat_times, frame_times, bpm)
    return AudioFeatures(
        bpm=bpm,
        beat_times=beat_times,
        downbeat_times=downbeat_times,
        onset_times=onset_times,
        section_times=section_times,
        frame_times=frame_times,
        onset_strength=onset_strength.astype(np.float32, copy=False),
        rms=rms.astype(np.float32, copy=False),
        low_energy=low_energy.astype(np.float32, copy=False),
        novelty=novelty.astype(np.float32, copy=False),
        confidence=confidence,
    )


def value_at_time(values: np.ndarray, frame_times: np.ndarray, time_sec: float) -> float:
    if values.size == 0 or frame_times.size == 0:
        return 0.0
    index = int(np.searchsorted(frame_times, time_sec, side="left"))
    index = max(0, min(index, len(values) - 1))
    return float(values[index])


def nearest_distance(times: np.ndarray, time_sec: float) -> float:
    if times.size == 0:
        return 999.0
    index = int(np.searchsorted(times, time_sec))
    candidates = []
    if index < len(times):
        candidates.append(abs(float(times[index]) - time_sec))
    if index > 0:
        candidates.append(abs(float(times[index - 1]) - time_sec))
    return min(candidates) if candidates else 999.0


def _track_beats(onset_strength: np.ndarray, sample_rate: int) -> tuple[float, np.ndarray]:
    import librosa

    if onset_strength.size == 0 or float(np.max(onset_strength)) <= 0.001:
        return 0.0, np.array([], dtype=np.float32)

    tempo, beats = librosa.beat.beat_track(
        onset_envelope=onset_strength,
        sr=sample_rate,
        hop_length=HOP_LENGTH,
        units="time",
        trim=True,
    )
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo.reshape(-1)[0]) if tempo.size else 0.0
    return float(tempo), np.asarray(beats, dtype=np.float32)


def _pick_onsets(onset_strength: np.ndarray, frame_times: np.ndarray, duration: float) -> np.ndarray:
    if onset_strength.size == 0 or float(np.max(onset_strength)) <= 0.001:
        return np.array([], dtype=np.float32)

    threshold = max(0.18, float(np.percentile(onset_strength, 72)))
    min_distance_frames = max(1, int(round(0.09 / _frame_step(frame_times))))
    peaks, _ = find_peaks(onset_strength, height=threshold, distance=min_distance_frames)
    times = frame_times[peaks]
    times = times[(times >= 0.0) & (times <= duration)]
    return np.asarray(times, dtype=np.float32)


def _pick_sections(novelty: np.ndarray, frame_times: np.ndarray, duration: float) -> np.ndarray:
    if novelty.size == 0 or float(np.max(novelty)) <= 0.001 or duration < 12.0:
        return np.array([], dtype=np.float32)

    threshold = max(0.35, float(np.percentile(novelty, 88)))
    min_distance_frames = max(1, int(round(6.0 / _frame_step(frame_times))))
    peaks, _ = find_peaks(novelty, height=threshold, distance=min_distance_frames)
    times = frame_times[peaks]
    times = times[(times >= 4.0) & (times <= duration - 2.0)]
    return np.asarray(times, dtype=np.float32)


def _infer_downbeats(
    beat_times: np.ndarray,
    onset_strength: np.ndarray,
    low_energy: np.ndarray,
    frame_times: np.ndarray,
) -> np.ndarray:
    if beat_times.size < 8:
        return np.array([], dtype=np.float32)

    beat_scores = np.array(
        [
            value_at_time(onset_strength, frame_times, float(t))
            + 0.35 * value_at_time(low_energy, frame_times, float(t))
            for t in beat_times
        ],
        dtype=np.float32,
    )
    phase_scores = []
    for phase in range(4):
        phase_values = beat_scores[phase::4]
        phase_scores.append(float(np.mean(phase_values)) if phase_values.size else 0.0)
    best_phase = int(np.argmax(phase_scores))
    return np.asarray(beat_times[best_phase::4], dtype=np.float32)


def _analysis_confidence(
    samples: np.ndarray,
    onset_strength: np.ndarray,
    beat_times: np.ndarray,
    frame_times: np.ndarray,
    bpm: float,
) -> float:
    if _is_silence(samples) or onset_strength.size == 0 or bpm <= 0.0:
        return 0.0

    onset_peak = float(np.percentile(onset_strength, 95))
    onset_floor = float(np.percentile(onset_strength, 45))
    contrast = np.clip((onset_peak - onset_floor) / max(onset_peak, 1e-6), 0.0, 1.0)

    if beat_times.size >= 4:
        intervals = np.diff(beat_times)
        regularity = 1.0 - np.clip(float(np.std(intervals) / max(np.mean(intervals), 1e-6)), 0.0, 1.0)
        beat_strength = float(np.mean([value_at_time(onset_strength, frame_times, float(t)) for t in beat_times]))
    else:
        regularity = 0.0
        beat_strength = 0.0

    energy = np.clip(float(np.sqrt(np.mean(np.square(samples)))) * 8.0, 0.0, 1.0)
    confidence = 0.38 * contrast + 0.32 * regularity + 0.2 * np.clip(beat_strength, 0.0, 1.0) + 0.1 * energy
    return float(np.clip(confidence, 0.0, 1.0))


def _low_frequency_energy(samples: np.ndarray, sample_rate: int, length: int) -> np.ndarray:
    import librosa

    stft = np.abs(librosa.stft(samples, n_fft=FRAME_LENGTH, hop_length=HOP_LENGTH))
    frequencies = librosa.fft_frequencies(sr=sample_rate, n_fft=FRAME_LENGTH)
    low_mask = frequencies <= 180.0
    if not np.any(low_mask):
        return np.zeros(length, dtype=np.float32)
    low = np.mean(stft[low_mask, :], axis=0)
    return _fit_length(_normalize(low), length)


def _section_novelty(samples: np.ndarray, sample_rate: int, length: int) -> np.ndarray:
    import librosa

    mel = librosa.feature.melspectrogram(
        y=samples,
        sr=sample_rate,
        hop_length=HOP_LENGTH,
        n_fft=FRAME_LENGTH,
        n_mels=48,
        power=2.0,
    )
    db = librosa.power_to_db(mel, ref=np.max)
    diff = np.maximum(0.0, np.diff(db, axis=1))
    novelty = np.mean(diff, axis=0)
    novelty = np.pad(novelty, (1, 0), mode="constant")
    if novelty.size >= 9:
        kernel = np.ones(9, dtype=np.float32) / 9.0
        novelty = np.convolve(novelty, kernel, mode="same")
    return _fit_length(_normalize(novelty), length)


def _normalize(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    if values.size == 0:
        return values
    values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    low = float(np.percentile(values, 5))
    high = float(np.percentile(values, 95))
    if high <= low + 1e-9:
        return np.zeros_like(values, dtype=np.float32)
    return np.clip((values - low) / (high - low), 0.0, 1.0).astype(np.float32)


def _fit_length(values: np.ndarray, length: int) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    if values.size == length:
        return values
    if values.size == 0:
        return np.zeros(length, dtype=np.float32)
    if values.size > length:
        return values[:length]
    return np.pad(values, (0, length - values.size), mode="edge")


def _is_silence(samples: np.ndarray) -> bool:
    if samples.size == 0:
        return True
    return float(np.max(np.abs(samples))) < 1e-5 or float(np.sqrt(np.mean(np.square(samples)))) < 1e-6


def _frame_step(frame_times: np.ndarray) -> float:
    if frame_times.size < 2:
        return HOP_LENGTH / 22050.0
    return max(1e-6, float(np.median(np.diff(frame_times))))

