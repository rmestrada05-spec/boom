"""Song analysis utilities for timestamping important musical events.

This module focuses on practical production workflows:
- estimate BPM from onset activity
- timestamp likely bass/synth/guitar hit points
- timestamp lead-vocal and background-vocal entry points
- provide additional key markers (kick, snare, section changes, drop candidates)

The event labeling is heuristic-based, so each event carries a confidence score.
"""

from __future__ import annotations

import json
import math
import pathlib
import wave
from dataclasses import asdict, dataclass, field

import numpy as np


@dataclass(frozen=True)
class TimestampEvent:
    """A single timestamped event candidate."""

    time_seconds: float
    confidence: float


@dataclass(frozen=True)
class SongAnalysisReport:
    """Structured output of a song analysis pass."""

    source_path: str
    sample_rate: int
    duration_seconds: float
    bpm: float | None
    beat_timestamps: tuple[float, ...]
    events_by_type: dict[str, tuple[TimestampEvent, ...]]
    warnings: tuple[str, ...] = field(default_factory=tuple)


def analyze_song(file_path: str, target_sample_rate: int = 22050) -> SongAnalysisReport:
    """Analyze a song recording and estimate event timestamps by category."""
    signal, sample_rate, warnings = _load_audio(file_path, target_sample_rate)
    duration = len(signal) / sample_rate if sample_rate > 0 else 0.0

    if duration <= 0.05:
        raise ValueError("Audio is too short to analyze.")

    frame_size = 2048
    hop_size = 512
    frames = _frame_audio(signal, frame_size=frame_size, hop_size=hop_size)
    frame_times = (np.arange(frames.shape[0]) * hop_size) / sample_rate

    window = np.hanning(frame_size).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(frames * window, axis=1)).astype(np.float32)
    freqs = np.fft.rfftfreq(frame_size, d=1.0 / sample_rate)

    onset_env = _build_onset_envelope(spectrum)
    onset_env = _smooth(onset_env, window_size=3)
    onset_env_norm = _normalize(onset_env)
    onset_indices = _peak_indices(
        onset_env_norm,
        threshold=max(0.24, float(np.percentile(onset_env_norm, 68))),
        min_gap_frames=max(1, int((0.07 * sample_rate) / hop_size)),
    )

    bpm = _estimate_bpm(onset_env_norm, sample_rate=sample_rate, hop_size=hop_size)
    beat_timestamps = _estimate_beat_times(
        frame_times=frame_times,
        onset_indices=onset_indices,
        bpm=bpm,
        duration_seconds=duration,
    )

    total_energy = spectrum.sum(axis=1) + 1e-9
    band_sub = _band_energy(spectrum, freqs, 20.0, 90.0)
    band_bass = _band_energy(spectrum, freqs, 90.0, 180.0)
    band_low_mid = _band_energy(spectrum, freqs, 180.0, 500.0)
    band_mid = _band_energy(spectrum, freqs, 500.0, 2000.0)
    band_presence = _band_energy(spectrum, freqs, 2000.0, 4500.0)
    band_air = _band_energy(spectrum, freqs, 4500.0, 12000.0)
    band_voice = _band_energy(spectrum, freqs, 250.0, 3400.0)

    ratio_sub = band_sub / total_energy
    ratio_bass = band_bass / total_energy
    ratio_low_mid = band_low_mid / total_energy
    ratio_mid = band_mid / total_energy
    ratio_presence = band_presence / total_energy
    ratio_air = band_air / total_energy
    ratio_voice = band_voice / total_energy

    centroid = (spectrum * freqs).sum(axis=1) / total_energy
    centroid_norm = np.clip(centroid / 4500.0, 0.0, 1.0)
    flatness = _spectral_flatness(spectrum)
    flatness_norm = np.clip(flatness * 2.5, 0.0, 1.0)
    harmonicity = np.clip(1.0 - (flatness * 1.9), 0.0, 1.0)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    rms_norm = _normalize(rms)
    zcr = _zero_crossing_rate(frames)
    zcr_focus = np.exp(-((zcr - 0.11) ** 2) / 0.01)

    bass_score = _normalize(
        (0.58 * (ratio_sub + ratio_bass))
        + (0.22 * (1.0 - centroid_norm))
        + (0.20 * onset_env_norm)
    )
    synth_score = _normalize(
        (0.34 * (ratio_mid + ratio_presence))
        + (0.35 * harmonicity)
        + (0.19 * onset_env_norm)
        + (0.12 * np.exp(-((centroid - 1300.0) ** 2) / (2.0 * 1100.0**2)))
    )
    guitar_score = _normalize(
        (0.30 * (ratio_low_mid + ratio_mid))
        + (0.18 * ratio_presence)
        + (0.24 * onset_env_norm)
        + (0.16 * zcr_focus)
        + (0.12 * harmonicity)
    )
    lead_vocal_score = _normalize(
        (0.50 * ratio_voice)
        + (0.23 * harmonicity)
        + (0.20 * rms_norm)
        + (0.07 * (1.0 - onset_env_norm))
    )
    background_vocal_score = _normalize(
        (0.52 * ratio_voice)
        + (0.24 * harmonicity)
        + (0.24 * (1.0 - rms_norm))
    )
    kick_score = _normalize(
        (0.45 * (ratio_sub + ratio_bass))
        + (0.35 * onset_env_norm)
        + (0.20 * flatness_norm)
    )
    snare_score = _normalize(
        (0.44 * (ratio_mid + ratio_presence))
        + (0.34 * onset_env_norm)
        + (0.22 * flatness_norm)
    )

    spectral_novelty = _normalize(
        np.concatenate(
            [[0.0], np.linalg.norm(np.diff(np.log1p(spectrum), axis=0), axis=1)]
        )
    )
    bass_growth = _normalize(
        np.maximum(0.0, np.diff(_smooth(ratio_sub + ratio_bass, 9), prepend=0.0))
    )

    bass_hits = _extract_from_onsets(
        frame_times,
        onset_indices,
        bass_score,
        threshold=max(0.52, float(np.percentile(bass_score[onset_indices], 65)) if len(onset_indices) else 0.52),
        min_gap_seconds=0.08,
    )
    synth_hits = _extract_from_onsets(
        frame_times,
        onset_indices,
        synth_score,
        threshold=max(0.48, float(np.percentile(synth_score[onset_indices], 62)) if len(onset_indices) else 0.48),
        min_gap_seconds=0.08,
    )
    guitar_hits = _extract_from_onsets(
        frame_times,
        onset_indices,
        guitar_score,
        threshold=max(0.50, float(np.percentile(guitar_score[onset_indices], 65)) if len(onset_indices) else 0.50),
        min_gap_seconds=0.10,
    )
    kick_hits = _extract_from_onsets(
        frame_times,
        onset_indices,
        kick_score,
        threshold=max(0.53, float(np.percentile(kick_score[onset_indices], 67)) if len(onset_indices) else 0.53),
        min_gap_seconds=0.08,
    )
    snare_hits = _extract_from_onsets(
        frame_times,
        onset_indices,
        snare_score,
        threshold=max(0.54, float(np.percentile(snare_score[onset_indices], 70)) if len(onset_indices) else 0.54),
        min_gap_seconds=0.10,
    )

    lead_threshold = max(0.46, float(np.percentile(lead_vocal_score, 78)))
    lead_mask = lead_vocal_score >= lead_threshold
    lead_entries = _extract_segments(
        frame_times=frame_times,
        score=lead_vocal_score,
        active_mask=lead_mask,
        min_duration_seconds=0.14,
    )

    background_threshold = max(0.42, float(np.percentile(background_vocal_score, 70)))
    background_mask = (background_vocal_score >= background_threshold) & (~lead_mask)
    background_entries = _extract_segments(
        frame_times=frame_times,
        score=background_vocal_score,
        active_mask=background_mask,
        min_duration_seconds=0.14,
    )

    section_changes = _extract_peak_events(
        frame_times=frame_times,
        score=spectral_novelty,
        threshold=max(0.42, float(np.percentile(spectral_novelty, 88))),
        min_gap_seconds=2.8,
        limit=30,
    )
    drop_candidates = _extract_peak_events(
        frame_times=frame_times,
        score=bass_growth * onset_env_norm,
        threshold=max(0.34, float(np.percentile(bass_growth * onset_env_norm, 86))),
        min_gap_seconds=1.8,
        limit=30,
    )

    if len(onset_indices) < 8:
        warnings.append(
            "Low onset activity detected; timestamp precision may be reduced."
        )
    if bpm is None:
        warnings.append(
            "Could not confidently estimate BPM from onsets."
        )

    events_by_type = {
        "bass_hits": bass_hits,
        "synth_hits": synth_hits,
        "guitar_hits": guitar_hits,
        "lead_vocal_entries": lead_entries,
        "background_vocal_entries": background_entries,
        "kick_hits": kick_hits,
        "snare_hits": snare_hits,
        "section_changes": section_changes,
        "drop_candidates": drop_candidates,
    }

    return SongAnalysisReport(
        source_path=file_path,
        sample_rate=sample_rate,
        duration_seconds=round(duration, 3),
        bpm=round(bpm, 2) if bpm is not None else None,
        beat_timestamps=tuple(round(ts, 3) for ts in beat_timestamps),
        events_by_type=events_by_type,
        warnings=tuple(warnings),
    )


def analysis_to_json(report: SongAnalysisReport) -> str:
    """Serialize song analysis report as formatted JSON."""
    return json.dumps(asdict(report), indent=2)


def analysis_to_pretty_text(
    report: SongAnalysisReport, max_timestamps_per_type: int = 20
) -> str:
    """Render song analysis report in a readable summary form."""
    bpm_text = f"{report.bpm:.2f}" if report.bpm is not None else "unknown"
    lines = [
        f"Song analysis: {report.source_path}",
        f"- Duration: {report.duration_seconds:.2f}s",
        f"- Sample rate: {report.sample_rate} Hz",
        f"- Estimated BPM: {bpm_text}",
        f"- Beat timestamps detected: {len(report.beat_timestamps)}",
    ]

    if report.beat_timestamps:
        beat_preview = ", ".join(
            f"{ts:.3f}" for ts in report.beat_timestamps[:max_timestamps_per_type]
        )
        lines.append(f"  preview beats: {beat_preview}")

    for event_type, events in report.events_by_type.items():
        lines.append(f"- {event_type}: {len(events)}")
        if not events:
            continue
        preview = ", ".join(
            f"{event.time_seconds:.3f}(c={event.confidence:.2f})"
            for event in events[:max_timestamps_per_type]
        )
        lines.append(f"  preview: {preview}")

    if report.warnings:
        lines.append("Warnings:")
        for warning in report.warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines)


def _load_audio(file_path: str, target_sample_rate: int) -> tuple[np.ndarray, int, list[str]]:
    path = pathlib.Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    warnings: list[str] = []
    ext = path.suffix.lower()
    if ext == ".wav":
        signal, sample_rate = _load_wav(path)
    else:
        signal, sample_rate = _load_with_optional_librosa(path)
        warnings.append(
            "Non-WAV input loaded with optional backend; decode accuracy depends on local codecs."
        )

    if sample_rate != target_sample_rate:
        signal = _resample_linear(signal, sample_rate, target_sample_rate)
        sample_rate = target_sample_rate
        warnings.append(
            f"Resampled audio to {target_sample_rate} Hz for analysis consistency."
        )

    if signal.size == 0:
        raise ValueError("Could not decode audio content.")
    return signal.astype(np.float32), sample_rate, warnings


def _load_wav(path: pathlib.Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        raw = wav_file.readframes(frame_count)

    if sample_width == 1:
        data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        data = (data - 128.0) / 128.0
    elif sample_width == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 3:
        bytes_array = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        signed = (
            bytes_array[:, 0].astype(np.int32)
            | (bytes_array[:, 1].astype(np.int32) << 8)
            | (bytes_array[:, 2].astype(np.int32) << 16)
        )
        signed = np.where(signed & 0x800000, signed - 0x1000000, signed)
        data = signed.astype(np.float32) / 8388608.0
    elif sample_width == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")

    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data.astype(np.float32), sample_rate


def _load_with_optional_librosa(path: pathlib.Path) -> tuple[np.ndarray, int]:
    try:
        import librosa  # type: ignore
    except ModuleNotFoundError as exc:
        raise ValueError(
            "Only WAV files are supported without optional dependencies. "
            "Install librosa to analyze MP3/AAC/other formats."
        ) from exc

    signal, sample_rate = librosa.load(str(path), sr=None, mono=True)
    return signal.astype(np.float32), int(sample_rate)


def _resample_linear(signal: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate or signal.size == 0:
        return signal
    duration = signal.size / source_rate
    target_length = max(1, int(round(duration * target_rate)))
    source_positions = np.linspace(0.0, duration, num=signal.size, endpoint=False)
    target_positions = np.linspace(0.0, duration, num=target_length, endpoint=False)
    return np.interp(target_positions, source_positions, signal).astype(np.float32)


def _frame_audio(signal: np.ndarray, frame_size: int, hop_size: int) -> np.ndarray:
    if signal.size < frame_size:
        signal = np.pad(signal, (0, frame_size - signal.size))

    frame_count = 1 + math.ceil((signal.size - frame_size) / hop_size)
    total_size = (frame_count - 1) * hop_size + frame_size
    if total_size > signal.size:
        signal = np.pad(signal, (0, total_size - signal.size))

    strides = (signal.strides[0] * hop_size, signal.strides[0])
    shape = (frame_count, frame_size)
    return np.lib.stride_tricks.as_strided(signal, shape=shape, strides=strides).copy()


def _build_onset_envelope(spectrum: np.ndarray) -> np.ndarray:
    if spectrum.shape[0] <= 1:
        return np.zeros(spectrum.shape[0], dtype=np.float32)
    diffs = np.diff(spectrum, axis=0)
    positive_diffs = np.maximum(diffs, 0.0)
    flux = positive_diffs.sum(axis=1)
    return np.concatenate([[0.0], flux]).astype(np.float32)


def _estimate_bpm(
    onset_envelope: np.ndarray,
    sample_rate: int,
    hop_size: int,
    min_bpm: int = 70,
    max_bpm: int = 210,
) -> float | None:
    if onset_envelope.size < 8:
        return None

    centered = onset_envelope - np.mean(onset_envelope)
    std = np.std(centered)
    if std < 1e-8:
        return None
    centered = centered / std

    autocorr = np.correlate(centered, centered, mode="full")[centered.size - 1 :]
    lag_min = max(1, int(round((60.0 * sample_rate) / (max_bpm * hop_size))))
    lag_max = min(
        autocorr.size - 1,
        int(round((60.0 * sample_rate) / (min_bpm * hop_size))),
    )
    if lag_max <= lag_min:
        return None

    segment = autocorr[lag_min : lag_max + 1]
    best_lag = lag_min + int(np.argmax(segment))
    bpm = (60.0 * sample_rate) / (hop_size * best_lag)

    # Pull octave errors toward a practical range.
    while bpm < 80.0:
        bpm *= 2.0
    while bpm > 190.0:
        bpm /= 2.0

    return float(bpm)


def _estimate_beat_times(
    frame_times: np.ndarray,
    onset_indices: np.ndarray,
    bpm: float | None,
    duration_seconds: float,
) -> tuple[float, ...]:
    if bpm is None or bpm <= 0:
        return tuple(round(float(frame_times[idx]), 3) for idx in onset_indices[:2000])

    period = 60.0 / bpm
    anchor = float(frame_times[int(onset_indices[0])]) if onset_indices.size else 0.0
    beat_times = np.arange(anchor, duration_seconds + period * 0.5, period)
    return tuple(round(float(ts), 3) for ts in beat_times)


def _spectral_flatness(spectrum: np.ndarray) -> np.ndarray:
    eps = 1e-10
    geometric = np.exp(np.mean(np.log(spectrum + eps), axis=1))
    arithmetic = np.mean(spectrum + eps, axis=1)
    return geometric / arithmetic


def _band_energy(
    spectrum: np.ndarray, freqs: np.ndarray, low_hz: float, high_hz: float
) -> np.ndarray:
    mask = (freqs >= low_hz) & (freqs < high_hz)
    if not np.any(mask):
        return np.zeros(spectrum.shape[0], dtype=np.float32)
    return spectrum[:, mask].sum(axis=1)


def _zero_crossing_rate(frames: np.ndarray) -> np.ndarray:
    if frames.shape[1] <= 1:
        return np.zeros(frames.shape[0], dtype=np.float32)
    signs = np.signbit(frames)
    crossings = np.count_nonzero(signs[:, 1:] != signs[:, :-1], axis=1)
    return crossings / float(frames.shape[1] - 1)


def _peak_indices(series: np.ndarray, threshold: float, min_gap_frames: int) -> np.ndarray:
    if series.size < 3:
        return np.array([], dtype=np.int32)
    min_gap_frames = max(1, min_gap_frames)
    candidate_indices = np.where(
        (series[1:-1] > series[:-2])
        & (series[1:-1] >= series[2:])
        & (series[1:-1] >= threshold)
    )[0] + 1

    if candidate_indices.size == 0:
        return np.array([], dtype=np.int32)

    selected: list[int] = [int(candidate_indices[0])]
    for idx in candidate_indices[1:]:
        idx = int(idx)
        if idx - selected[-1] >= min_gap_frames:
            selected.append(idx)
        elif series[idx] > series[selected[-1]]:
            selected[-1] = idx
    return np.asarray(selected, dtype=np.int32)


def _extract_from_onsets(
    frame_times: np.ndarray,
    onset_indices: np.ndarray,
    score: np.ndarray,
    threshold: float,
    min_gap_seconds: float,
) -> tuple[TimestampEvent, ...]:
    if onset_indices.size == 0:
        return tuple()

    chosen: list[TimestampEvent] = []
    last_time = -1e9
    for idx in onset_indices:
        score_value = float(score[int(idx)])
        if score_value < threshold:
            continue
        timestamp = float(frame_times[int(idx)])
        if timestamp - last_time < min_gap_seconds:
            if chosen and score_value > chosen[-1].confidence:
                chosen[-1] = TimestampEvent(
                    time_seconds=round(timestamp, 3),
                    confidence=round(min(score_value, 1.0), 3),
                )
                last_time = timestamp
            continue
        chosen.append(
            TimestampEvent(
                time_seconds=round(timestamp, 3),
                confidence=round(min(score_value, 1.0), 3),
            )
        )
        last_time = timestamp
    return tuple(chosen)


def _extract_peak_events(
    frame_times: np.ndarray,
    score: np.ndarray,
    threshold: float,
    min_gap_seconds: float,
    limit: int,
) -> tuple[TimestampEvent, ...]:
    if score.size == 0:
        return tuple()

    frame_gap = max(1, int(min_gap_seconds / np.mean(np.diff(frame_times)) if frame_times.size > 1 else 1))
    indices = _peak_indices(score, threshold=threshold, min_gap_frames=frame_gap)
    if indices.size == 0:
        return tuple()

    events = [
        TimestampEvent(
            time_seconds=round(float(frame_times[idx]), 3),
            confidence=round(float(min(score[idx], 1.0)), 3),
        )
        for idx in indices[:limit]
    ]
    return tuple(events)


def _extract_segments(
    frame_times: np.ndarray,
    score: np.ndarray,
    active_mask: np.ndarray,
    min_duration_seconds: float,
) -> tuple[TimestampEvent, ...]:
    if frame_times.size == 0 or score.size == 0:
        return tuple()
    if frame_times.size != active_mask.size or frame_times.size != score.size:
        raise ValueError("Segment inputs must share the same frame dimension.")

    frame_duration = float(np.mean(np.diff(frame_times))) if frame_times.size > 1 else 0.0
    min_frames = max(1, int(round(min_duration_seconds / frame_duration))) if frame_duration > 0 else 1

    events: list[TimestampEvent] = []
    start_idx: int | None = None
    for idx, is_active in enumerate(active_mask):
        if is_active and start_idx is None:
            start_idx = idx
        if not is_active and start_idx is not None:
            if idx - start_idx >= min_frames:
                confidence = float(np.mean(score[start_idx:idx]))
                events.append(
                    TimestampEvent(
                        time_seconds=round(float(frame_times[start_idx]), 3),
                        confidence=round(min(confidence, 1.0), 3),
                    )
                )
            start_idx = None

    if start_idx is not None and frame_times.size - start_idx >= min_frames:
        confidence = float(np.mean(score[start_idx:]))
        events.append(
            TimestampEvent(
                time_seconds=round(float(frame_times[start_idx]), 3),
                confidence=round(min(confidence, 1.0), 3),
            )
        )
    return tuple(events)


def _smooth(series: np.ndarray, window_size: int) -> np.ndarray:
    if window_size <= 1 or series.size == 0:
        return series
    kernel = np.ones(window_size, dtype=np.float32) / float(window_size)
    return np.convolve(series, kernel, mode="same")


def _normalize(series: np.ndarray) -> np.ndarray:
    max_value = float(np.max(np.abs(series))) if series.size else 0.0
    if max_value <= 1e-12:
        return np.zeros_like(series, dtype=np.float32)
    return (series / max_value).astype(np.float32)
