"""Audio analysis pipeline for timestamping modern EDM-rap elements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import librosa
import numpy as np

from song_analyzer.garageband import get_preset_for_element


TARGET_SAMPLE_RATE = 22_050
N_FFT = 2_048
HOP_LENGTH = 512
MAX_ANALYSIS_SECONDS = 8 * 60
MELODIC_PITCH_KEYS = {
    "lead_synth_melody",
    "chords_pads",
    "counter_melody",
    "synth_brass_stabs",
    "main_vocals",
    "adlibs",
    "vocal_chops",
    "vocal_fx_processing",
    "atmospheres_textures",
    "growls_screeches",
    "plucks",
    "supersaw",
    "vocal_one_shots",
}


ELEMENT_SPECS: dict[str, dict[str, Any]] = {
    "kick": {
        "label": "Kick / 808 Kick",
        "quantile": 0.90,
        "min_duration": 0.05,
        "max_gap": 0.04,
        "max_segments": 220,
        "min_confidence": 0.45,
        "smooth": 3,
    },
    "bass_808_sub": {
        "label": "808 Bass / Sub-bass",
        "quantile": 0.82,
        "min_duration": 0.16,
        "max_gap": 0.10,
        "max_segments": 120,
        "min_confidence": 0.42,
        "smooth": 7,
    },
    "bass_midrange": {
        "label": "Mid-range Bass Layer",
        "quantile": 0.84,
        "min_duration": 0.12,
        "max_gap": 0.10,
        "max_segments": 100,
        "min_confidence": 0.42,
        "smooth": 7,
    },
    "snare_clap": {
        "label": "Snare / Clap",
        "quantile": 0.89,
        "min_duration": 0.05,
        "max_gap": 0.04,
        "max_segments": 220,
        "min_confidence": 0.44,
        "smooth": 3,
    },
    "hihat_rolls": {
        "label": "Hi-hats / Rolls",
        "quantile": 0.88,
        "min_duration": 0.04,
        "max_gap": 0.05,
        "max_segments": 250,
        "min_confidence": 0.42,
        "smooth": 3,
    },
    "percussion_secondary": {
        "label": "Secondary Percussion",
        "quantile": 0.86,
        "min_duration": 0.06,
        "max_gap": 0.06,
        "max_segments": 180,
        "min_confidence": 0.41,
        "smooth": 5,
    },
    "lead_synth_melody": {
        "label": "Lead Synth / Main Melody",
        "quantile": 0.85,
        "min_duration": 0.14,
        "max_gap": 0.12,
        "max_segments": 120,
        "min_confidence": 0.44,
        "smooth": 9,
    },
    "chords_pads": {
        "label": "Chords / Pads",
        "quantile": 0.82,
        "min_duration": 0.24,
        "max_gap": 0.16,
        "max_segments": 100,
        "min_confidence": 0.44,
        "smooth": 11,
    },
    "counter_melody": {
        "label": "Counter-melody",
        "quantile": 0.86,
        "min_duration": 0.08,
        "max_gap": 0.08,
        "max_segments": 150,
        "min_confidence": 0.43,
        "smooth": 5,
    },
    "synth_brass_stabs": {
        "label": "Synth Brass / Stabs",
        "quantile": 0.90,
        "min_duration": 0.05,
        "max_gap": 0.04,
        "max_segments": 160,
        "min_confidence": 0.45,
        "smooth": 3,
    },
    "main_vocals": {
        "label": "Main Vocals",
        "quantile": 0.84,
        "min_duration": 0.20,
        "max_gap": 0.14,
        "max_segments": 120,
        "min_confidence": 0.42,
        "smooth": 11,
    },
    "adlibs": {
        "label": "Ad-libs",
        "quantile": 0.88,
        "min_duration": 0.07,
        "max_gap": 0.07,
        "max_segments": 160,
        "min_confidence": 0.43,
        "smooth": 5,
    },
    "vocal_chops": {
        "label": "Vocal Chops",
        "quantile": 0.89,
        "min_duration": 0.06,
        "max_gap": 0.06,
        "max_segments": 140,
        "min_confidence": 0.43,
        "smooth": 5,
    },
    "vocal_fx_processing": {
        "label": "Vocal FX Moments",
        "quantile": 0.86,
        "min_duration": 0.08,
        "max_gap": 0.08,
        "max_segments": 140,
        "min_confidence": 0.42,
        "smooth": 7,
    },
    "risers": {
        "label": "Risers",
        "quantile": 0.88,
        "min_duration": 0.24,
        "max_gap": 0.14,
        "max_segments": 60,
        "min_confidence": 0.44,
        "smooth": 13,
    },
    "impacts_hits": {
        "label": "Impacts / Hits",
        "quantile": 0.90,
        "min_duration": 0.05,
        "max_gap": 0.04,
        "max_segments": 120,
        "min_confidence": 0.45,
        "smooth": 3,
    },
    "sweeps_downlifters": {
        "label": "Downlifters / Reverse Sweeps",
        "quantile": 0.88,
        "min_duration": 0.16,
        "max_gap": 0.10,
        "max_segments": 80,
        "min_confidence": 0.43,
        "smooth": 11,
    },
    "white_noise_sweeps": {
        "label": "White Noise Sweeps",
        "quantile": 0.86,
        "min_duration": 0.14,
        "max_gap": 0.10,
        "max_segments": 90,
        "min_confidence": 0.42,
        "smooth": 11,
    },
    "foley_sfx": {
        "label": "Foley / One-shot SFX",
        "quantile": 0.90,
        "min_duration": 0.05,
        "max_gap": 0.05,
        "max_segments": 100,
        "min_confidence": 0.44,
        "smooth": 5,
    },
    "transitions_fills": {
        "label": "Transitions / Drum Fills",
        "quantile": 0.89,
        "min_duration": 0.06,
        "max_gap": 0.08,
        "max_segments": 120,
        "min_confidence": 0.44,
        "smooth": 7,
    },
    "atmospheres_textures": {
        "label": "Atmospheres / Textures",
        "quantile": 0.80,
        "min_duration": 0.30,
        "max_gap": 0.18,
        "max_segments": 80,
        "min_confidence": 0.40,
        "smooth": 15,
    },
    "growls_screeches": {
        "label": "Growls / Screeches",
        "quantile": 0.88,
        "min_duration": 0.10,
        "max_gap": 0.08,
        "max_segments": 90,
        "min_confidence": 0.43,
        "smooth": 7,
    },
    "counter_808s": {
        "label": "Counter 808 Layer",
        "quantile": 0.89,
        "min_duration": 0.05,
        "max_gap": 0.05,
        "max_segments": 140,
        "min_confidence": 0.43,
        "smooth": 5,
    },
    "reese_bass": {
        "label": "Reese Bass Character",
        "quantile": 0.86,
        "min_duration": 0.16,
        "max_gap": 0.12,
        "max_segments": 80,
        "min_confidence": 0.43,
        "smooth": 9,
    },
    "plucks": {
        "label": "Synth Plucks",
        "quantile": 0.89,
        "min_duration": 0.05,
        "max_gap": 0.05,
        "max_segments": 180,
        "min_confidence": 0.43,
        "smooth": 5,
    },
    "supersaw": {
        "label": "Supersaw Stack",
        "quantile": 0.84,
        "min_duration": 0.18,
        "max_gap": 0.14,
        "max_segments": 70,
        "min_confidence": 0.43,
        "smooth": 11,
    },
    "vocal_one_shots": {
        "label": "Vocal One-shots",
        "quantile": 0.90,
        "min_duration": 0.05,
        "max_gap": 0.05,
        "max_segments": 120,
        "min_confidence": 0.44,
        "smooth": 3,
    },
}


SUBGENRE_BOOSTS: dict[str, dict[str, float]] = {
    "general edm-rap": {},
    "hybrid trap": {
        "growls_screeches": 1.15,
        "impacts_hits": 1.10,
        "risers": 1.10,
        "supersaw": 1.08,
    },
    "rage": {
        "growls_screeches": 1.22,
        "supersaw": 1.15,
        "hihat_rolls": 1.08,
        "lead_synth_melody": 1.10,
    },
    "phonk-edm": {
        "counter_808s": 1.18,
        "reese_bass": 1.12,
        "atmospheres_textures": 1.10,
        "foley_sfx": 1.12,
    },
    "jersey-club influenced": {
        "kick": 1.12,
        "snare_clap": 1.10,
        "hihat_rolls": 1.12,
        "percussion_secondary": 1.15,
    },
}


@dataclass
class DetectionSegment:
    start: float
    end: float
    confidence: float


def _normalize(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return values
    low = float(np.min(values))
    high = float(np.max(values))
    if high - low < 1e-9:
        return np.zeros_like(values)
    return (values - low) / (high - low)


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return values
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(values, kernel, mode="same")


def _band_energy(magnitude: np.ndarray, freqs: np.ndarray, low: float, high: float) -> np.ndarray:
    mask = (freqs >= low) & (freqs < high)
    if not np.any(mask):
        return np.zeros(magnitude.shape[1], dtype=float)
    return magnitude[mask].sum(axis=0)


def _trim_all(features: list[np.ndarray]) -> list[np.ndarray]:
    min_len = min(len(feature) for feature in features)
    return [feature[:min_len] for feature in features]


def _positive_gradient(values: np.ndarray) -> np.ndarray:
    return _normalize(np.maximum(np.gradient(values), 0.0))


def _negative_gradient(values: np.ndarray) -> np.ndarray:
    return _normalize(np.maximum(-np.gradient(values), 0.0))


def _weighted_score(length: int, components: list[tuple[np.ndarray, float]]) -> np.ndarray:
    score = np.zeros(length, dtype=float)
    for values, weight in components:
        score = score + (values * weight)
    return _normalize(score)


def _estimate_bpm(onset_envelope: np.ndarray, sr: int) -> float:
    tempo, _ = librosa.beat.beat_track(
        onset_envelope=onset_envelope,
        sr=sr,
        hop_length=HOP_LENGTH,
        start_bpm=140,
    )
    bpm = float(np.atleast_1d(tempo)[0])
    if not np.isfinite(bpm) or bpm <= 0:
        fallback = librosa.feature.tempo(
            onset_envelope=onset_envelope,
            sr=sr,
            hop_length=HOP_LENGTH,
            aggregate=np.median,
        )
        bpm = float(np.atleast_1d(fallback)[0])

    while bpm < 70:
        bpm *= 2
    while bpm > 200:
        bpm /= 2
    return round(bpm, 2)


def _format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    remainder = seconds - (minutes * 60)
    return f"{minutes:02d}:{remainder:05.2f}"


def _extract_pitch_contour(y: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    """Estimate frame-level pitch contour in MIDI numbers."""
    try:
        f0_hz, _, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            frame_length=N_FFT,
            hop_length=HOP_LENGTH,
            sr=sr,
        )
    except Exception:  # noqa: BLE001
        return np.array([], dtype=float), np.array([], dtype=float)

    if f0_hz is None or len(f0_hz) == 0:
        return np.array([], dtype=float), np.array([], dtype=float)

    pitch_times = librosa.frames_to_time(np.arange(len(f0_hz)), sr=sr, hop_length=HOP_LENGTH)
    pitch_midi = np.full(len(f0_hz), np.nan, dtype=float)
    valid_mask = np.isfinite(f0_hz)
    if np.any(valid_mask):
        pitch_midi[valid_mask] = librosa.hz_to_midi(f0_hz[valid_mask])
    return pitch_times, pitch_midi


def _pitch_movement_label(delta_semitones: float) -> str:
    if delta_semitones >= 0.75:
        return "up"
    if delta_semitones <= -0.75:
        return "down"
    return "flat"


def _segment_pitch_payload(
    start_seconds: float,
    end_seconds: float,
    pitch_times: np.ndarray,
    pitch_midi: np.ndarray,
) -> dict[str, Any] | None:
    if pitch_times.size == 0 or pitch_midi.size == 0:
        return None

    left_idx = int(np.searchsorted(pitch_times, start_seconds, side="left"))
    right_idx = int(np.searchsorted(pitch_times, end_seconds, side="right"))
    if right_idx <= left_idx:
        return None

    segment_notes = pitch_midi[left_idx:right_idx]
    finite = segment_notes[np.isfinite(segment_notes)]
    if finite.size < 3:
        return None

    midpoint = max(1, finite.size // 2)
    first_half = finite[:midpoint]
    second_half = finite[midpoint:]
    if second_half.size == 0:
        second_half = first_half

    pitch_start = float(np.median(first_half))
    pitch_end = float(np.median(second_half))
    pitch_mid = float(np.median(finite))
    pitch_var = float(np.percentile(finite, 90) - np.percentile(finite, 10))
    movement_delta = pitch_end - pitch_start
    pitch_class = int(round(pitch_mid)) % 12

    return {
        "pitch_midi": round(pitch_mid, 2),
        "pitch_midi_start": round(pitch_start, 2),
        "pitch_midi_end": round(pitch_end, 2),
        "pitch_variation_semitones": round(pitch_var, 2),
        "pitch_movement_delta": round(movement_delta, 2),
        "pitch_movement": _pitch_movement_label(movement_delta),
        "pitch_class": pitch_class,
    }


def _extract_segments(
    score: np.ndarray,
    times: np.ndarray,
    frame_duration: float,
    threshold: float,
    min_duration: float,
    max_gap: float,
) -> list[DetectionSegment]:
    active = score >= threshold
    active_indices = np.flatnonzero(active)
    if active_indices.size == 0:
        return []

    groups: list[tuple[int, int]] = []
    start_idx = int(active_indices[0])
    previous_idx = int(active_indices[0])
    for idx in active_indices[1:]:
        idx = int(idx)
        if idx == previous_idx + 1:
            previous_idx = idx
            continue
        groups.append((start_idx, previous_idx))
        start_idx = idx
        previous_idx = idx
    groups.append((start_idx, previous_idx))

    merged: list[tuple[int, int]] = []
    for group_start, group_end in groups:
        if not merged:
            merged.append((group_start, group_end))
            continue
        prev_start, prev_end = merged[-1]
        prev_end_time = times[prev_end] + frame_duration
        current_start_time = times[group_start]
        if (current_start_time - prev_end_time) <= max_gap:
            merged[-1] = (prev_start, group_end)
        else:
            merged.append((group_start, group_end))

    segments: list[DetectionSegment] = []
    for group_start, group_end in merged:
        start_time = float(times[group_start])
        end_time = float(times[group_end] + frame_duration)
        duration = end_time - start_time
        if duration < min_duration:
            continue
        confidence = float(np.mean(score[group_start : group_end + 1]))
        segments.append(DetectionSegment(start=start_time, end=end_time, confidence=confidence))

    return segments


def _build_scores(features: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    length = len(features["sub"])
    low_end = _normalize((0.62 * features["sub"]) + (0.38 * features["bass"]))
    high_air = _normalize(features["high"] + features["air"])
    mid_high = _normalize(features["mid"] + features["high"])
    voice_like = _normalize(
        (0.50 * features["voice_band"])
        + (0.25 * features["harm_ratio"])
        + (0.25 * features["mid"])
    )

    scores = {
        "kick": _weighted_score(
            length,
            [
                (features["perc_ratio"], 0.46),
                (low_end, 0.40),
                (features["onset"], 0.35),
                (features["high"], -0.14),
            ],
        ),
        "bass_808_sub": _weighted_score(
            length,
            [
                (features["sub"], 0.62),
                (features["bass"], 0.33),
                (features["rms"], 0.22),
                (features["onset"], -0.18),
            ],
        ),
        "bass_midrange": _weighted_score(
            length,
            [
                (features["bass"], 0.45),
                (features["low_mid"], 0.36),
                (features["flatness"], 0.18),
                (features["perc_ratio"], 0.08),
            ],
        ),
        "snare_clap": _weighted_score(
            length,
            [
                (features["perc_ratio"], 0.44),
                (mid_high, 0.34),
                (features["onset"], 0.40),
                (features["sub"], -0.18),
            ],
        ),
        "hihat_rolls": _weighted_score(
            length,
            [
                (features["perc_ratio"], 0.38),
                (high_air, 0.48),
                (features["onset"], 0.44),
            ],
        ),
        "percussion_secondary": _weighted_score(
            length,
            [
                (features["perc_ratio"], 0.48),
                (mid_high, 0.28),
                (features["onset"], 0.24),
            ],
        ),
        "lead_synth_melody": _weighted_score(
            length,
            [
                (features["harm_ratio"], 0.44),
                (mid_high, 0.35),
                (features["centroid"], 0.24),
                (features["onset"], 0.18),
            ],
        ),
        "chords_pads": _weighted_score(
            length,
            [
                (features["harm_ratio"], 0.52),
                (features["low_mid"], 0.26),
                (features["mid"], 0.20),
                (features["onset"], -0.28),
                (features["flatness"], -0.20),
            ],
        ),
        "counter_melody": _weighted_score(
            length,
            [
                (features["harm_ratio"], 0.42),
                (features["mid"], 0.30),
                (features["onset"], 0.22),
                (features["centroid"], 0.12),
            ],
        ),
        "synth_brass_stabs": _weighted_score(
            length,
            [
                (features["harm_ratio"], 0.28),
                (features["mid"], 0.30),
                (features["onset"], 0.46),
                (features["rms"], 0.22),
            ],
        ),
        "main_vocals": _weighted_score(
            length,
            [
                (voice_like, 0.58),
                (features["harm_ratio"], 0.24),
                (features["onset"], 0.08),
                (features["flatness"], -0.15),
            ],
        ),
        "adlibs": _weighted_score(
            length,
            [
                (voice_like, 0.44),
                (features["high"], 0.24),
                (features["onset"], 0.36),
                (features["flatness"], 0.10),
            ],
        ),
        "vocal_chops": _weighted_score(
            length,
            [
                (voice_like, 0.38),
                (features["onset"], 0.48),
                (features["flatness"], 0.20),
                (features["high"], 0.14),
            ],
        ),
        "vocal_fx_processing": _weighted_score(
            length,
            [
                (voice_like, 0.36),
                (features["air"], 0.24),
                (features["flatness"], 0.24),
                (features["rolloff"], 0.20),
            ],
        ),
        "risers": _weighted_score(
            length,
            [
                (features["centroid_up"], 0.44),
                (features["rolloff_up"], 0.36),
                (features["air"], 0.22),
            ],
        ),
        "impacts_hits": _weighted_score(
            length,
            [
                (features["onset"], 0.52),
                (low_end, 0.24),
                (high_air, 0.24),
            ],
        ),
        "sweeps_downlifters": _weighted_score(
            length,
            [
                (features["centroid_down"], 0.50),
                (features["rolloff_down"], 0.34),
                (features["air"], 0.16),
            ],
        ),
        "white_noise_sweeps": _weighted_score(
            length,
            [
                (features["flatness"], 0.44),
                (high_air, 0.40),
                (features["centroid_change"], 0.20),
            ],
        ),
        "foley_sfx": _weighted_score(
            length,
            [
                (features["flatness"], 0.36),
                (mid_high, 0.36),
                (features["onset"], 0.28),
                (features["harm_ratio"], -0.18),
            ],
        ),
        "transitions_fills": _weighted_score(
            length,
            [
                (features["onset"], 0.38),
                (features["perc_ratio"], 0.32),
                (features["energy_change"], 0.30),
            ],
        ),
        "atmospheres_textures": _weighted_score(
            length,
            [
                (features["flatness"], 0.34),
                (features["harm_ratio"], 0.24),
                (features["onset"], -0.36),
                (features["rms"], 0.16),
                (features["air"], 0.12),
            ],
        ),
        "growls_screeches": _weighted_score(
            length,
            [
                (features["flatness"], 0.34),
                (features["mid"], 0.34),
                (features["bass"], 0.24),
                (features["onset"], 0.18),
            ],
        ),
        "counter_808s": _weighted_score(
            length,
            [
                (features["sub"], 0.56),
                (features["onset"], 0.34),
                (features["flatness"], 0.20),
            ],
        ),
        "reese_bass": _weighted_score(
            length,
            [
                (features["bass"], 0.42),
                (features["mid"], 0.30),
                (features["harm_ratio"], 0.18),
                (features["flatness"], 0.14),
            ],
        ),
        "plucks": _weighted_score(
            length,
            [
                (features["harm_ratio"], 0.36),
                (mid_high, 0.34),
                (features["onset"], 0.42),
            ],
        ),
        "supersaw": _weighted_score(
            length,
            [
                (features["harm_ratio"], 0.48),
                (mid_high, 0.34),
                (features["air"], 0.20),
                (features["onset"], -0.10),
            ],
        ),
        "vocal_one_shots": _weighted_score(
            length,
            [
                (voice_like, 0.42),
                (features["onset"], 0.44),
                (features["high"], 0.20),
            ],
        ),
    }
    return scores


def analyze_song(file_path: str, subgenre_profile: str = "General EDM-rap") -> dict[str, Any]:
    """Analyze a song and return timestamped detected elements with GarageBand recreation info."""
    y, sr = librosa.load(
        file_path,
        sr=TARGET_SAMPLE_RATE,
        mono=True,
        duration=MAX_ANALYSIS_SECONDS,
    )
    if y.size < (sr * 2):
        raise ValueError("Audio is too short. Upload at least 2 seconds.")

    duration_seconds = float(librosa.get_duration(y=y, sr=sr))
    pitch_times, pitch_midi = _extract_pitch_contour(y, sr)

    magnitude = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP_LENGTH))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
    times = librosa.frames_to_time(np.arange(magnitude.shape[1]), sr=sr, hop_length=HOP_LENGTH)

    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH)
    rms = librosa.feature.rms(S=magnitude).reshape(-1)
    flatness = librosa.feature.spectral_flatness(S=magnitude).reshape(-1)
    centroid = librosa.feature.spectral_centroid(S=magnitude, sr=sr).reshape(-1)
    rolloff = librosa.feature.spectral_rolloff(S=magnitude, sr=sr, roll_percent=0.90).reshape(-1)
    low_mid = _band_energy(magnitude, freqs, 250, 1_000)
    sub = _band_energy(magnitude, freqs, 20, 90)
    bass = _band_energy(magnitude, freqs, 90, 250)
    mid = _band_energy(magnitude, freqs, 1_000, 4_000)
    high = _band_energy(magnitude, freqs, 4_000, 10_000)
    air = _band_energy(magnitude, freqs, 10_000, 16_000)
    voice_band = _band_energy(magnitude, freqs, 250, 4_000)

    harmonic_audio, percussive_audio = librosa.effects.hpss(y)
    harmonic_mag = np.abs(librosa.stft(harmonic_audio, n_fft=N_FFT, hop_length=HOP_LENGTH))
    percussive_mag = np.abs(librosa.stft(percussive_audio, n_fft=N_FFT, hop_length=HOP_LENGTH))
    harmonic_energy = harmonic_mag.sum(axis=0)
    percussive_energy = percussive_mag.sum(axis=0)
    total_hp_energy = harmonic_energy + percussive_energy + 1e-9
    harm_ratio = harmonic_energy / total_hp_energy
    perc_ratio = percussive_energy / total_hp_energy

    aligned = _trim_all(
        [
            times,
            onset,
            rms,
            flatness,
            centroid,
            rolloff,
            low_mid,
            sub,
            bass,
            mid,
            high,
            air,
            voice_band,
            harm_ratio,
            perc_ratio,
        ]
    )
    (
        times,
        onset,
        rms,
        flatness,
        centroid,
        rolloff,
        low_mid,
        sub,
        bass,
        mid,
        high,
        air,
        voice_band,
        harm_ratio,
        perc_ratio,
    ) = aligned

    feature_map = {
        "onset": _normalize(onset),
        "rms": _normalize(rms),
        "flatness": _normalize(flatness),
        "centroid": _normalize(centroid),
        "rolloff": _normalize(rolloff),
        "low_mid": _normalize(low_mid),
        "sub": _normalize(sub),
        "bass": _normalize(bass),
        "mid": _normalize(mid),
        "high": _normalize(high),
        "air": _normalize(air),
        "voice_band": _normalize(voice_band),
        "harm_ratio": np.clip(harm_ratio, 0.0, 1.0),
        "perc_ratio": np.clip(perc_ratio, 0.0, 1.0),
    }
    feature_map["centroid_up"] = _positive_gradient(feature_map["centroid"])
    feature_map["centroid_down"] = _negative_gradient(feature_map["centroid"])
    feature_map["rolloff_up"] = _positive_gradient(feature_map["rolloff"])
    feature_map["rolloff_down"] = _negative_gradient(feature_map["rolloff"])
    feature_map["centroid_change"] = _normalize(np.abs(np.gradient(feature_map["centroid"])))
    feature_map["energy_change"] = _normalize(np.abs(np.gradient(feature_map["rms"])))

    raw_scores = _build_scores(feature_map)

    boosts = SUBGENRE_BOOSTS.get(subgenre_profile.lower(), {})
    for element_key, multiplier in boosts.items():
        if element_key in raw_scores:
            raw_scores[element_key] = np.clip(raw_scores[element_key] * multiplier, 0.0, 1.0)

    frame_duration = HOP_LENGTH / sr
    detections: list[dict[str, Any]] = []

    for element_key, spec in ELEMENT_SPECS.items():
        if element_key not in raw_scores:
            continue

        smoothed = _moving_average(raw_scores[element_key], int(spec["smooth"]))
        score = _normalize(smoothed)
        threshold = max(float(np.quantile(score, float(spec["quantile"]))), 0.40)
        segments = _extract_segments(
            score=score,
            times=times,
            frame_duration=frame_duration,
            threshold=threshold,
            min_duration=float(spec["min_duration"]),
            max_gap=float(spec["max_gap"]),
        )
        segments = [segment for segment in segments if segment.confidence >= float(spec["min_confidence"])]
        segments.sort(key=lambda segment: segment.confidence, reverse=True)
        segments = segments[: int(spec["max_segments"])]
        segments.sort(key=lambda segment: segment.start)

        preset = get_preset_for_element(element_key)
        for segment in segments:
            row: dict[str, Any] = {
                "element_key": element_key,
                "element": spec["label"],
                "start_seconds": round(segment.start, 3),
                "end_seconds": round(segment.end, 3),
                "start_timestamp": _format_timestamp(segment.start),
                "end_timestamp": _format_timestamp(segment.end),
                "confidence": round(segment.confidence, 3),
                "garageband_similar_sound": preset.similar_sound,
                "garageband_patch": preset.patch,
                "suggested_effects": list(preset.effects),
                "recreation_notes": preset.recreation_notes,
            }
            if element_key in MELODIC_PITCH_KEYS:
                pitch_payload = _segment_pitch_payload(
                    start_seconds=segment.start,
                    end_seconds=segment.end,
                    pitch_times=pitch_times,
                    pitch_midi=pitch_midi,
                )
                if pitch_payload:
                    row.update(pitch_payload)
            detections.append(row)

    detections.sort(key=lambda detection: (detection["start_seconds"], -detection["confidence"]))

    bpm = _estimate_bpm(feature_map["onset"], sr)
    avg_confidence = float(np.mean([d["confidence"] for d in detections])) if detections else 0.0

    notes = [
        "Pitch contour metadata is attached to melodic detections for better MIDI movement.",
        "Use AI stem-separated mode in the app for best isolation quality.",
    ]
    return {
        "bpm": bpm,
        "duration_seconds": round(duration_seconds, 2),
        "analyzed_seconds": round(min(duration_seconds, MAX_ANALYSIS_SECONDS), 2),
        "subgenre_profile": subgenre_profile,
        "overall_detection_confidence": round(avg_confidence, 3),
        "pitch_frames_analyzed": int(np.sum(np.isfinite(pitch_midi))) if pitch_midi.size else 0,
        "detections": detections,
        "notes": notes,
    }
