"""Song splitter and clip-cache pipeline for GarageBand import workflows.

This module builds on song analysis timestamps and extracts cleaner source
clips (bass/synth/guitar/vocals/etc.) into a cache that can be reused.
"""

from __future__ import annotations

import json
import math
import pathlib
import uuid
import wave
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import numpy as np

from .song_analyzer import (
    SongAnalysisReport,
    TimestampEvent,
    _frame_audio,
    _load_audio,
    analyze_song,
)

DEFAULT_SPLIT_EVENT_TYPES: tuple[str, ...] = (
    "bass_hits",
    "synth_hits",
    "guitar_hits",
    "lead_vocal_entries",
    "background_vocal_entries",
    "kick_hits",
    "snare_hits",
)


@dataclass(frozen=True)
class CachedClip:
    """Metadata for an extracted clip saved in cache."""

    clip_id: str
    event_type: str
    timestamp_seconds: float
    confidence: float
    source_path: str
    clip_path: str
    sample_rate: int
    bit_depth: int
    duration_seconds: float
    created_at_utc: str
    extraction_profile: str


@dataclass(frozen=True)
class SplitterReport:
    """Result summary for a split-to-cache operation."""

    source_path: str
    cache_dir: str
    clip_count: int
    clips_by_type: dict[str, tuple[CachedClip, ...]]
    manifest_path: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


def split_song_to_cache(
    file_path: str,
    cache_dir: str = ".garageband_cache",
    event_types: tuple[str, ...] | list[str] | None = None,
    max_events_per_type: int = 12,
    min_confidence: float = 0.45,
    pre_roll_seconds: float = 0.08,
    post_roll_seconds: float = 0.90,
    target_sample_rate: int = 48000,
    target_bit_depth: int = 24,
    extraction_profile: str = "clean_4k",
) -> SplitterReport:
    """Split key sounds into cacheable clips for GarageBand workflows."""
    if max_events_per_type < 1:
        raise ValueError("max_events_per_type must be at least 1")
    if target_bit_depth not in (16, 24):
        raise ValueError("target_bit_depth must be 16 or 24")

    selected_types = tuple(event_types) if event_types else DEFAULT_SPLIT_EVENT_TYPES
    cache_paths = _ensure_cache_structure(cache_dir)
    analysis = analyze_song(file_path)
    signal, sample_rate, decode_warnings = _load_audio(file_path, target_sample_rate)

    clips_by_type: dict[str, tuple[CachedClip, ...]] = {}
    all_created: list[CachedClip] = []
    warnings = list(analysis.warnings) + decode_warnings

    for event_type in selected_types:
        source_events = list(analysis.events_by_type.get(event_type, ()))
        if not source_events:
            clips_by_type[event_type] = tuple()
            continue

        chosen_events = _select_events(
            source_events,
            max_events=max_events_per_type,
            min_confidence=min_confidence,
        )
        created_for_type: list[CachedClip] = []
        for event in chosen_events:
            extracted = _extract_event_clip(
                signal=signal,
                sample_rate=sample_rate,
                event_type=event_type,
                event=event,
                pre_roll_seconds=pre_roll_seconds,
                post_roll_seconds=post_roll_seconds,
                extraction_profile=extraction_profile,
            )
            if extracted.size == 0:
                continue
            clip_meta = _store_clip(
                clip_audio=extracted,
                event_type=event_type,
                event=event,
                source_path=file_path,
                clip_directory=cache_paths["clips"],
                sample_rate=target_sample_rate,
                bit_depth=target_bit_depth,
                extraction_profile=extraction_profile,
            )
            created_for_type.append(clip_meta)
            all_created.append(clip_meta)

        clips_by_type[event_type] = tuple(created_for_type)

    _append_to_cache_index(cache_paths["index"], all_created)
    manifest_path = _write_import_manifest(
        cache_paths["manifest"],
        file_path=file_path,
        analysis=analysis,
        clips=all_created,
    )

    if not all_created:
        warnings.append(
            "No clips passed confidence/selection filters. Try lowering min_confidence."
        )

    return SplitterReport(
        source_path=file_path,
        cache_dir=str(pathlib.Path(cache_dir).resolve()),
        clip_count=len(all_created),
        clips_by_type=clips_by_type,
        manifest_path=manifest_path,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def list_cached_clips(
    cache_dir: str = ".garageband_cache",
    event_type: str | None = None,
    limit: int | None = None,
) -> tuple[CachedClip, ...]:
    """List previously extracted clips from cache index."""
    cache_paths = _ensure_cache_structure(cache_dir)
    entries = _load_cache_index(cache_paths["index"])
    if event_type:
        entries = [entry for entry in entries if entry.event_type == event_type]
    if limit is not None and limit >= 0:
        entries = entries[:limit]
    return tuple(entries)


def splitter_report_to_json(report: SplitterReport) -> str:
    """Serialize split report as JSON."""
    return json.dumps(asdict(report), indent=2)


def splitter_report_to_pretty_text(
    report: SplitterReport, max_preview_per_type: int = 8
) -> str:
    """Render split report in a terminal-friendly format."""
    lines = [
        f"Split source: {report.source_path}",
        f"- Cache directory: {report.cache_dir}",
        f"- Total clips extracted: {report.clip_count}",
        f"- Import manifest: {report.manifest_path}",
    ]
    for event_type, clips in report.clips_by_type.items():
        lines.append(f"- {event_type}: {len(clips)}")
        if not clips:
            continue
        preview = ", ".join(
            f"{pathlib.Path(clip.clip_path).name}@{clip.timestamp_seconds:.3f}s(c={clip.confidence:.2f})"
            for clip in clips[:max_preview_per_type]
        )
        lines.append(f"  preview: {preview}")
    if report.warnings:
        lines.append("Warnings:")
        for warning in report.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def cached_clips_to_pretty_text(clips: tuple[CachedClip, ...]) -> str:
    """Render cached clips as a compact list."""
    if not clips:
        return "No cached clips found."

    lines = [f"Cached clips: {len(clips)}"]
    for clip in clips:
        lines.append(
            "- "
            + f"{clip.clip_id} | {clip.event_type} | {clip.timestamp_seconds:.3f}s "
            + f"(c={clip.confidence:.2f}) | {clip.clip_path}"
        )
    return "\n".join(lines)


def cached_clips_to_json(clips: tuple[CachedClip, ...]) -> str:
    """Serialize cached clips as JSON."""
    return json.dumps([asdict(clip) for clip in clips], indent=2)


def _ensure_cache_structure(cache_dir: str) -> dict[str, str]:
    root = pathlib.Path(cache_dir).resolve()
    clips_dir = root / "clips"
    root.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    index_path = root / "index.json"
    manifest_path = root / "import_manifest.txt"
    if not index_path.exists():
        index_path.write_text("[]", encoding="utf-8")
    return {
        "root": str(root),
        "clips": str(clips_dir),
        "index": str(index_path),
        "manifest": str(manifest_path),
    }


def _load_cache_index(index_path: str) -> list[CachedClip]:
    path = pathlib.Path(index_path)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    clips: list[CachedClip] = []
    for item in payload:
        try:
            clips.append(CachedClip(**item))
        except TypeError:
            continue
    return clips


def _append_to_cache_index(index_path: str, new_entries: list[CachedClip]) -> None:
    existing = _load_cache_index(index_path)
    merged = existing + new_entries
    pathlib.Path(index_path).write_text(
        json.dumps([asdict(entry) for entry in merged], indent=2),
        encoding="utf-8",
    )


def _write_import_manifest(
    manifest_path: str,
    file_path: str,
    analysis: SongAnalysisReport,
    clips: list[CachedClip],
) -> str:
    path = pathlib.Path(manifest_path)
    root = path.parent
    clip_folder = root / "clips"

    lines = [
        "GarageBand Clip Import Manifest",
        f"Source: {file_path}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Estimated BPM: {analysis.bpm if analysis.bpm is not None else 'unknown'}",
        "",
        "How to use in GarageBand (Mac):",
        "1) Open GarageBand project.",
        "2) Open Finder to the clip cache folder below.",
        "3) Drag any clip file from Finder into a GarageBand track.",
        "",
        f"Clip folder: {clip_folder}",
        "",
        "Suggested Finder command:",
        f"open \"{clip_folder}\"",
        "",
        "Clip list:",
    ]

    for clip in clips:
        lines.append(
            f"- {clip.event_type} @ {clip.timestamp_seconds:.3f}s (c={clip.confidence:.2f}) -> {clip.clip_path}"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _select_events(
    events: list[TimestampEvent], max_events: int, min_confidence: float
) -> list[TimestampEvent]:
    filtered = [event for event in events if event.confidence >= min_confidence]
    if not filtered:
        # fallback to strongest events if confidence filter is too strict
        filtered = sorted(events, key=lambda event: event.confidence, reverse=True)[:max_events]
        return sorted(filtered, key=lambda event: event.time_seconds)

    if len(filtered) <= max_events:
        return sorted(filtered, key=lambda event: event.time_seconds)

    # preserve coverage over time by combining top-confidence picks and spacing.
    filtered_sorted = sorted(filtered, key=lambda event: event.time_seconds)
    stride = max(1, len(filtered_sorted) // max_events)
    spread_picks = [filtered_sorted[idx] for idx in range(0, len(filtered_sorted), stride)]
    confidence_picks = sorted(filtered, key=lambda event: event.confidence, reverse=True)[:max_events]
    combined = {(
        round(event.time_seconds, 3),
        round(event.confidence, 3),
    ): event for event in spread_picks + confidence_picks}
    selected = sorted(combined.values(), key=lambda event: event.confidence, reverse=True)[:max_events]
    return sorted(selected, key=lambda event: event.time_seconds)


def _extract_event_clip(
    signal: np.ndarray,
    sample_rate: int,
    event_type: str,
    event: TimestampEvent,
    pre_roll_seconds: float,
    post_roll_seconds: float,
    extraction_profile: str,
) -> np.ndarray:
    start_time = max(0.0, event.time_seconds - pre_roll_seconds)
    end_time = min(len(signal) / sample_rate, event.time_seconds + post_roll_seconds)
    if end_time <= start_time:
        return np.array([], dtype=np.float32)

    start_idx = int(round(start_time * sample_rate))
    end_idx = int(round(end_time * sample_rate))
    clip = signal[start_idx:end_idx].astype(np.float32)
    if clip.size == 0:
        return clip

    event_local_time = max(0.0, event.time_seconds - start_time)
    enhanced = _enhance_source_clip(
        clip,
        sample_rate=sample_rate,
        event_type=event_type,
        event_local_time=event_local_time,
        extraction_profile=extraction_profile,
    )
    return enhanced


def _store_clip(
    clip_audio: np.ndarray,
    event_type: str,
    event: TimestampEvent,
    source_path: str,
    clip_directory: str,
    sample_rate: int,
    bit_depth: int,
    extraction_profile: str,
) -> CachedClip:
    clip_id = uuid.uuid4().hex[:12]
    file_name = (
        f"{event_type}__t{event.time_seconds:08.3f}__c{event.confidence:.2f}__{clip_id}.wav"
        .replace(":", "_")
        .replace("/", "_")
    )
    clip_path = str(pathlib.Path(clip_directory) / file_name)
    _write_wav_mono(clip_path, clip_audio, sample_rate, bit_depth)
    return CachedClip(
        clip_id=clip_id,
        event_type=event_type,
        timestamp_seconds=round(event.time_seconds, 3),
        confidence=round(event.confidence, 3),
        source_path=source_path,
        clip_path=clip_path,
        sample_rate=sample_rate,
        bit_depth=bit_depth,
        duration_seconds=round(float(len(clip_audio) / sample_rate), 3),
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        extraction_profile=extraction_profile,
    )


def _write_wav_mono(path: str, signal: np.ndarray, sample_rate: int, bit_depth: int) -> None:
    clipped = np.clip(signal, -1.0, 1.0)
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setframerate(sample_rate)
        if bit_depth == 16:
            wav_file.setsampwidth(2)
            pcm = (clipped * 32767.0).astype("<i2")
            wav_file.writeframes(pcm.tobytes())
        elif bit_depth == 24:
            wav_file.setsampwidth(3)
            int_data = np.round(clipped * 8388607.0).astype(np.int32)
            byte_data = np.empty((int_data.size, 3), dtype=np.uint8)
            byte_data[:, 0] = (int_data & 0xFF).astype(np.uint8)
            byte_data[:, 1] = ((int_data >> 8) & 0xFF).astype(np.uint8)
            byte_data[:, 2] = ((int_data >> 16) & 0xFF).astype(np.uint8)
            wav_file.writeframes(byte_data.tobytes())
        else:
            raise ValueError("Unsupported bit depth. Use 16 or 24.")


def _enhance_source_clip(
    clip: np.ndarray,
    sample_rate: int,
    event_type: str,
    event_local_time: float,
    extraction_profile: str,
) -> np.ndarray:
    if clip.size < 1024:
        return _normalize_to_peak(clip, peak=0.95)

    n_fft = 4096 if clip.size >= 4096 else 2048
    hop = n_fft // 4
    stft = _stft(clip, n_fft=n_fft, hop_size=hop)
    magnitude = np.abs(stft)
    phase = np.angle(stft)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)
    frame_times = (np.arange(stft.shape[1]) * hop) / float(sample_rate)

    harmonic_mask, percussive_mask = _hpss_masks(magnitude)
    freq_profile = _frequency_profile(freqs, event_type)
    temporal_profile = _temporal_focus_profile(
        frame_times=frame_times,
        event_local_time=event_local_time,
        event_type=event_type,
    )
    denoise_mask = _spectral_denoise_mask(magnitude, profile=extraction_profile)

    hp_blend, perc_blend = _harmonic_percussive_blend(event_type)
    source_shape = (
        (hp_blend * harmonic_mask + perc_blend * percussive_mask)
        * freq_profile[:, None]
        * temporal_profile[None, :]
    )

    floor = 0.08 if extraction_profile == "clean_4k" else 0.12
    final_mask = np.clip(source_shape * denoise_mask + floor * freq_profile[:, None], 0.0, 1.0)
    enhanced_stft = magnitude * final_mask * np.exp(1j * phase)
    enhanced = _istft(enhanced_stft, n_fft=n_fft, hop_size=hop, output_length=clip.size)
    enhanced = _tonal_cleanup(enhanced, sample_rate, event_type, profile=extraction_profile)
    return _normalize_to_peak(enhanced, peak=0.95)


def _stft(signal: np.ndarray, n_fft: int, hop_size: int) -> np.ndarray:
    frames = _frame_audio(signal, frame_size=n_fft, hop_size=hop_size)
    window = np.hanning(n_fft).astype(np.float32)
    return np.fft.rfft(frames * window[None, :], axis=1).T


def _istft(
    stft_matrix: np.ndarray, n_fft: int, hop_size: int, output_length: int
) -> np.ndarray:
    frame_count = stft_matrix.shape[1]
    expected_len = (frame_count - 1) * hop_size + n_fft
    output = np.zeros(expected_len, dtype=np.float32)
    norm = np.zeros(expected_len, dtype=np.float32)
    window = np.hanning(n_fft).astype(np.float32)

    for frame_idx in range(frame_count):
        start = frame_idx * hop_size
        frame = np.fft.irfft(stft_matrix[:, frame_idx], n=n_fft).astype(np.float32)
        output[start : start + n_fft] += frame * window
        norm[start : start + n_fft] += window**2

    safe = norm > 1e-6
    output[safe] /= norm[safe]
    if output_length <= output.size:
        return output[:output_length]
    return np.pad(output, (0, output_length - output.size))


def _hpss_masks(magnitude: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    harmonic = _median_filter_axis(magnitude, kernel_size=11, axis=1)
    percussive = _median_filter_axis(magnitude, kernel_size=11, axis=0)
    denom = harmonic + percussive + 1e-8
    harmonic_mask = harmonic / denom
    percussive_mask = percussive / denom
    return harmonic_mask, percussive_mask


def _median_filter_axis(
    array: np.ndarray, kernel_size: int, axis: int
) -> np.ndarray:
    if kernel_size <= 1:
        return array
    kernel_size = kernel_size + 1 if kernel_size % 2 == 0 else kernel_size
    pad = kernel_size // 2

    if axis == 0:
        padded = np.pad(array, ((pad, pad), (0, 0)), mode="edge")
        output = np.empty_like(array)
        for idx in range(array.shape[0]):
            output[idx] = np.median(padded[idx : idx + kernel_size], axis=0)
        return output
    if axis == 1:
        padded = np.pad(array, ((0, 0), (pad, pad)), mode="edge")
        output = np.empty_like(array)
        for idx in range(array.shape[1]):
            output[:, idx] = np.median(padded[:, idx : idx + kernel_size], axis=1)
        return output
    raise ValueError("axis must be 0 or 1")


def _spectral_denoise_mask(magnitude: np.ndarray, profile: str) -> np.ndarray:
    base_percentile = 28 if profile == "clean_4k" else 22
    floor = np.percentile(magnitude, base_percentile, axis=1, keepdims=True)
    strength = 1.3 if profile == "clean_4k" else 1.1
    mask = np.clip((magnitude - floor * strength) / (magnitude + 1e-8), 0.0, 1.0)
    return mask


def _frequency_profile(freqs: np.ndarray, event_type: str) -> np.ndarray:
    # Frequency response curves are heuristic priors for source enhancement.
    def gaussian(center: float, width: float) -> np.ndarray:
        return np.exp(-0.5 * ((freqs - center) / max(1.0, width)) ** 2)

    low = 1.0 / (1.0 + np.exp((freqs - 130.0) / 28.0))
    mid = gaussian(850.0, 750.0)
    upper_mid = gaussian(2800.0, 1400.0)
    air = gaussian(7000.0, 3200.0)

    mapping: dict[str, np.ndarray] = {
        "bass_hits": np.clip(1.3 * low + 0.35 * gaussian(210.0, 120.0), 0.0, 1.0),
        "kick_hits": np.clip(1.2 * low + 0.25 * gaussian(2800.0, 1500.0), 0.0, 1.0),
        "snare_hits": np.clip(0.35 * low + 0.95 * upper_mid + 0.45 * air, 0.0, 1.0),
        "synth_hits": np.clip(0.55 * mid + 0.95 * upper_mid + 0.35 * air, 0.0, 1.0),
        "guitar_hits": np.clip(0.55 * gaussian(220.0, 150.0) + 0.8 * mid + 0.7 * upper_mid, 0.0, 1.0),
        "lead_vocal_entries": np.clip(0.45 * gaussian(220.0, 160.0) + 0.85 * mid + 0.95 * upper_mid, 0.0, 1.0),
        "background_vocal_entries": np.clip(0.35 * gaussian(240.0, 170.0) + 0.72 * mid + 0.95 * upper_mid + 0.40 * air, 0.0, 1.0),
    }
    profile = mapping.get(event_type, np.ones_like(freqs, dtype=np.float32))
    return np.maximum(profile.astype(np.float32), 0.03)


def _temporal_focus_profile(
    frame_times: np.ndarray, event_local_time: float, event_type: str
) -> np.ndarray:
    if frame_times.size == 0:
        return np.zeros(0, dtype=np.float32)

    if event_type in ("lead_vocal_entries", "background_vocal_entries"):
        sigma = 0.38
    elif event_type in ("guitar_hits", "synth_hits"):
        sigma = 0.22
    else:
        sigma = 0.14
    profile = np.exp(-0.5 * ((frame_times - event_local_time) / sigma) ** 2)
    return np.clip(0.45 + 0.55 * profile, 0.0, 1.0).astype(np.float32)


def _harmonic_percussive_blend(event_type: str) -> tuple[float, float]:
    if event_type in ("kick_hits", "snare_hits"):
        return 0.15, 0.95
    if event_type == "bass_hits":
        return 0.55, 0.50
    if event_type in ("synth_hits", "guitar_hits", "lead_vocal_entries", "background_vocal_entries"):
        return 0.95, 0.25
    return 0.6, 0.6


def _tonal_cleanup(
    signal: np.ndarray, sample_rate: int, event_type: str, profile: str
) -> np.ndarray:
    if signal.size == 0:
        return signal

    n = int(2 ** math.ceil(math.log2(signal.size)))
    spectrum = np.fft.rfft(np.pad(signal, (0, n - signal.size)))
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)
    gain = np.ones_like(freqs, dtype=np.float32)

    # Remove low rumble unless the target is low-end focused.
    if event_type not in ("bass_hits", "kick_hits"):
        high_pass = 1.0 / (1.0 + np.exp(-(freqs - 55.0) / 10.0))
        gain *= high_pass

    # Reduce mud and harshness for cleaner pulls.
    if profile == "clean_4k":
        mud_cut = 1.0 - 0.24 * np.exp(-0.5 * ((freqs - 280.0) / 140.0) ** 2)
        harsh_cut = 1.0 - 0.14 * np.exp(-0.5 * ((freqs - 4200.0) / 1800.0) ** 2)
        gain *= mud_cut * harsh_cut

    # Focus bandwidth by source type.
    if event_type == "bass_hits":
        low_pass = 1.0 / (1.0 + np.exp((freqs - 280.0) / 25.0))
        gain *= np.clip(low_pass + 0.10, 0.0, 1.0)
    elif event_type == "kick_hits":
        low_pass = 1.0 / (1.0 + np.exp((freqs - 6500.0) / 1200.0))
        gain *= np.clip(low_pass + 0.10, 0.0, 1.0)
    elif event_type == "snare_hits":
        high_pass = 1.0 / (1.0 + np.exp(-(freqs - 110.0) / 25.0))
        gain *= np.clip(high_pass, 0.0, 1.0)
    elif event_type in ("lead_vocal_entries", "background_vocal_entries"):
        high_pass = 1.0 / (1.0 + np.exp(-(freqs - 90.0) / 18.0))
        low_pass = 1.0 / (1.0 + np.exp((freqs - 9800.0) / 1700.0))
        gain *= np.clip(high_pass * low_pass + 0.08, 0.0, 1.0)

    processed = np.fft.irfft(spectrum * gain, n=n)[: signal.size].astype(np.float32)
    return processed


def _normalize_to_peak(signal: np.ndarray, peak: float = 0.95) -> np.ndarray:
    max_abs = float(np.max(np.abs(signal))) if signal.size else 0.0
    if max_abs < 1e-8:
        return signal.astype(np.float32)
    return (signal * (peak / max_abs)).astype(np.float32)
