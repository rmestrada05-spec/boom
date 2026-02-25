"""Post-export MIDI quality analysis against reference song detections."""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from statistics import median
from typing import Any

import numpy as np
from mido import MidiFile

from song_analyzer.garageband_export import DEFAULT_BPM, ELEMENT_MIDI_NOTE


MELODIC_KEYS = {
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
    "reese_bass",
    "plucks",
    "supersaw",
    "vocal_one_shots",
}


def _normalize_name(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def _extract_bpm_from_midi(midi: MidiFile) -> float | None:
    for track in midi.tracks:
        for message in track:
            if message.type == "set_tempo":
                if message.tempo <= 0:
                    return None
                return 60_000_000.0 / float(message.tempo)
    return None


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda pair: (pair[0], pair[1]))
    merged: list[tuple[float, float]] = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _duration_sum(intervals: list[tuple[float, float]]) -> float:
    return sum(max(0.0, end - start) for start, end in intervals)


def _overlap_duration(
    intervals_a: list[tuple[float, float]],
    intervals_b: list[tuple[float, float]],
) -> float:
    a = _merge_intervals(intervals_a)
    b = _merge_intervals(intervals_b)
    idx_a = 0
    idx_b = 0
    overlap = 0.0
    while idx_a < len(a) and idx_b < len(b):
        start_a, end_a = a[idx_a]
        start_b, end_b = b[idx_b]
        start = max(start_a, start_b)
        end = min(end_a, end_b)
        if end > start:
            overlap += end - start
        if end_a < end_b:
            idx_a += 1
        else:
            idx_b += 1
    return overlap


def _timing_score(reference_starts: list[float], midi_starts: list[float], tolerance: float = 0.35) -> float:
    if not reference_starts and not midi_starts:
        return 1.0
    if not reference_starts or not midi_starts:
        return 0.0

    nearest_distances = []
    for start in reference_starts:
        nearest = min(abs(start - midi_start) for midi_start in midi_starts)
        nearest_distances.append(nearest)
    median_distance = float(median(nearest_distances))
    return float(max(0.0, min(1.0, 1.0 - (median_distance / tolerance))))


def _density_score(reference_count: int, midi_count: int) -> float:
    if reference_count == 0 and midi_count == 0:
        return 1.0
    ratio = (midi_count + 1.0) / (reference_count + 1.0)
    return float(max(0.0, 1.0 - (abs(np.log2(ratio)) / 2.0)))


def _infer_element_key(
    track_name: str,
    note_values: list[int],
    normalized_label_to_key: dict[str, str],
    note_to_element: dict[int, str],
) -> str | None:
    normalized_track = _normalize_name(track_name)
    for normalized_label, element_key in normalized_label_to_key.items():
        if normalized_label and normalized_label in normalized_track:
            return element_key

    if note_values:
        dominant_note = max(set(note_values), key=note_values.count)
        by_note = note_to_element.get(dominant_note)
        if by_note:
            return by_note
    return None


def _parse_midi_intervals(
    midi_bytes: bytes,
    fallback_bpm: float,
    normalized_label_to_key: dict[str, str],
) -> dict[str, Any]:
    midi = MidiFile(file=BytesIO(midi_bytes))
    tempo_bpm = _extract_bpm_from_midi(midi)
    effective_bpm = tempo_bpm if tempo_bpm and tempo_bpm > 0 else float(fallback_bpm or DEFAULT_BPM)
    seconds_per_tick = 60.0 / (effective_bpm * midi.ticks_per_beat)
    note_to_element = {note: key for key, note in ELEMENT_MIDI_NOTE.items()}

    track_events: list[dict[str, Any]] = []
    total_note_count = 0
    malformed_note_count = 0

    for index, track in enumerate(midi.tracks):
        track_name = f"Track {index + 1}"
        abs_ticks = 0
        active_notes: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        raw_intervals: list[dict[str, Any]] = []

        for message in track:
            abs_ticks += int(message.time)
            if message.type == "track_name":
                track_name = message.name or track_name
            if message.type == "note_on" and message.velocity > 0:
                active_notes[(message.channel, message.note)].append((abs_ticks, int(message.velocity)))
                continue
            if message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
                key = (message.channel, message.note)
                if key not in active_notes or not active_notes[key]:
                    malformed_note_count += 1
                    continue
                start_tick, velocity = active_notes[key].pop()
                end_tick = max(abs_ticks, start_tick + 1)
                raw_intervals.append(
                    {
                        "start_seconds": start_tick * seconds_per_tick,
                        "end_seconds": end_tick * seconds_per_tick,
                        "note": int(message.note),
                        "velocity": int(velocity),
                    }
                )
                total_note_count += 1

        note_values = [item["note"] for item in raw_intervals]
        element_key = _infer_element_key(
            track_name=track_name,
            note_values=note_values,
            normalized_label_to_key=normalized_label_to_key,
            note_to_element=note_to_element,
        )
        track_events.append(
            {
                "track_name": track_name,
                "element_key": element_key,
                "intervals": raw_intervals,
            }
        )

    mapped_note_count = sum(len(track["intervals"]) for track in track_events if track["element_key"])
    return {
        "tempo_bpm": tempo_bpm,
        "effective_bpm": effective_bpm,
        "ticks_per_beat": midi.ticks_per_beat,
        "track_count": len(track_events),
        "total_note_count": total_note_count,
        "mapped_note_count": mapped_note_count,
        "mapped_ratio": (mapped_note_count / total_note_count) if total_note_count else 0.0,
        "malformed_note_count": malformed_note_count,
        "tracks": track_events,
    }


def analyze_midi_quality(
    midi_bytes: bytes,
    reference_result: dict[str, Any],
    expected_bpm: float | None = None,
) -> dict[str, Any]:
    """Compare a MIDI blueprint to detected reference song structure and format."""
    detections = list(reference_result.get("detections", []))
    reference_bpm = float(expected_bpm or reference_result.get("bpm") or DEFAULT_BPM)
    duration_seconds = float(
        reference_result.get("analyzed_seconds")
        or reference_result.get("duration_seconds")
        or 0.0
    )
    if duration_seconds <= 0:
        max_end = max((float(item["end_seconds"]) for item in detections), default=60.0)
        duration_seconds = max(60.0, max_end)

    normalized_label_to_key: dict[str, str] = {}
    for detection in detections:
        normalized_label_to_key[_normalize_name(str(detection["element"]))] = str(detection["element_key"])

    midi_info = _parse_midi_intervals(midi_bytes, fallback_bpm=reference_bpm, normalized_label_to_key=normalized_label_to_key)

    reference_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for detection in detections:
        reference_by_key[str(detection["element_key"])].append(detection)

    midi_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for track in midi_info["tracks"]:
        if not track["element_key"]:
            continue
        for interval in track["intervals"]:
            midi_by_key[str(track["element_key"])].append(interval)

    all_keys = set(reference_by_key.keys()) | set(midi_by_key.keys())
    element_rows: list[dict[str, Any]] = []
    weight_total = 0.0
    weighted_arrangement = 0.0
    weighted_timing = 0.0
    weighted_density = 0.0

    for element_key in sorted(all_keys):
        reference_items = reference_by_key.get(element_key, [])
        midi_items = midi_by_key.get(element_key, [])

        reference_intervals = [
            (float(item["start_seconds"]), float(item["end_seconds"])) for item in reference_items
        ]
        midi_intervals = [
            (float(item["start_seconds"]), float(item["end_seconds"])) for item in midi_items
        ]
        reference_duration = _duration_sum(reference_intervals)
        midi_duration = _duration_sum(midi_intervals)
        overlap = _overlap_duration(reference_intervals, midi_intervals)

        if reference_duration > 0:
            coverage = overlap / reference_duration
        else:
            coverage = 1.0 if midi_duration == 0 else 0.0
        if midi_duration > 0:
            precision = overlap / midi_duration
        else:
            precision = 1.0 if reference_duration == 0 else 0.0

        if (coverage + precision) > 0:
            f1 = (2.0 * coverage * precision) / (coverage + precision)
        else:
            f1 = 0.0

        reference_starts = [float(item["start_seconds"]) for item in reference_items]
        midi_starts = [float(item["start_seconds"]) for item in midi_items]
        timing = _timing_score(reference_starts, midi_starts)
        density = _density_score(len(reference_items), len(midi_items))
        combined = (0.6 * f1) + (0.2 * timing) + (0.2 * density)

        element_name = reference_items[0]["element"] if reference_items else element_key
        row = {
            "element_key": element_key,
            "element": element_name,
            "reference_regions": len(reference_items),
            "midi_regions": len(midi_items),
            "coverage": round(float(coverage), 3),
            "precision": round(float(precision), 3),
            "timing_score": round(float(timing), 3),
            "density_score": round(float(density), 3),
            "element_score": round(float(combined), 3),
        }
        element_rows.append(row)

        weight = max(reference_duration, 0.5)
        weight_total += weight
        weighted_arrangement += f1 * weight
        weighted_timing += timing * weight
        weighted_density += density * weight

    arrangement_score = (weighted_arrangement / weight_total) if weight_total else 0.0
    timing_score = (weighted_timing / weight_total) if weight_total else 0.0
    density_score = (weighted_density / weight_total) if weight_total else 0.0

    midi_tempo_bpm = midi_info["tempo_bpm"]
    if midi_tempo_bpm is None:
        tempo_score = 0.55
    else:
        tempo_diff_ratio = abs(midi_tempo_bpm - reference_bpm) / max(reference_bpm, 1e-9)
        tempo_score = max(0.0, 1.0 - (tempo_diff_ratio / 0.12))

    melodic_rows = [row for row in element_rows if row["element_key"] in MELODIC_KEYS and row["midi_regions"] > 0]
    melodic_note_scores = []
    for row in melodic_rows:
        key = row["element_key"]
        notes = [
            int(item["note"])
            for item in midi_by_key.get(key, [])
        ]
        unique_notes = len(set(notes))
        note_score = min(1.0, unique_notes / 4.0)
        melodic_note_scores.append(note_score)
    if melodic_rows:
        melodic_score = float(np.mean(melodic_note_scores))
    else:
        melodic_score = 0.45

    format_checks = [
        {
            "name": "Tempo event present",
            "passed": midi_tempo_bpm is not None,
            "details": "Missing tempo can cause GarageBand import mismatches."
            if midi_tempo_bpm is None
            else f"MIDI tempo: {midi_tempo_bpm:.2f} BPM",
        },
        {
            "name": "Contains note events",
            "passed": midi_info["total_note_count"] > 0,
            "details": f"Total notes: {midi_info['total_note_count']}",
        },
        {
            "name": "Has multiple tracks",
            "passed": midi_info["track_count"] >= 2,
            "details": f"Track count: {midi_info['track_count']}",
        },
        {
            "name": "Low malformed note events",
            "passed": midi_info["malformed_note_count"] == 0,
            "details": f"Malformed note events: {midi_info['malformed_note_count']}",
        },
        {
            "name": "Reference mapping coverage",
            "passed": midi_info["mapped_ratio"] >= 0.35,
            "details": f"Mapped note ratio: {midi_info['mapped_ratio']:.2f}",
        },
    ]
    format_score = sum(1.0 for check in format_checks if check["passed"]) / len(format_checks)

    overall_score = (
        (0.35 * arrangement_score)
        + (0.20 * timing_score)
        + (0.15 * density_score)
        + (0.10 * tempo_score)
        + (0.10 * format_score)
        + (0.10 * melodic_score)
    )
    overall_score = float(max(0.0, min(1.0, overall_score)))

    if overall_score >= 0.85:
        grade = "Excellent"
    elif overall_score >= 0.70:
        grade = "Good"
    elif overall_score >= 0.50:
        grade = "Needs Work"
    else:
        grade = "Poor"

    recommendations: list[str] = []
    if tempo_score < 0.70:
        recommendations.append("Set GarageBand project tempo to detected BPM and re-export MIDI.")
    if arrangement_score < 0.65:
        recommendations.append(
            "Arrangement overlap is low. Add/trim MIDI regions so section starts/stops match the timestamp table."
        )
    if timing_score < 0.65:
        recommendations.append(
            "Timing alignment is loose. Quantize regions to the beat grid and nudge starts to match reference hits."
        )
    if density_score < 0.65:
        recommendations.append(
            "MIDI event density is off. Increase/decrease note count per section to mirror the original energy."
        )
    if melodic_score < 0.60:
        recommendations.append(
            "Melodic note variety is too static. Add pitch movement/chord changes to better match the original contour."
        )
    failing_checks = [check for check in format_checks if not check["passed"]]
    if failing_checks:
        recommendations.append(
            "Fix MIDI formatting issues before import/export loops: "
            + "; ".join(check["name"] for check in failing_checks)
            + "."
        )

    weakest = sorted(
        [row for row in element_rows if row["reference_regions"] > 0],
        key=lambda row: row["element_score"],
    )[:5]
    for row in weakest:
        if row["element_score"] < 0.45:
            recommendations.append(
                f"Focus on '{row['element']}': low match score ({row['element_score']:.2f}). "
                "Adjust region timing and density first."
            )

    summary = (
        "This post-rip checker compares MIDI structure to the original audio analysis. "
        "It validates tempo, arrangement overlap, timing alignment, density, and formatting quality."
    )
    return {
        "overall_score": round(overall_score, 3),
        "grade": grade,
        "summary": summary,
        "scores": {
            "tempo_score": round(float(tempo_score), 3),
            "arrangement_score": round(float(arrangement_score), 3),
            "timing_score": round(float(timing_score), 3),
            "density_score": round(float(density_score), 3),
            "format_score": round(float(format_score), 3),
            "melodic_score": round(float(melodic_score), 3),
        },
        "reference_bpm": round(float(reference_bpm), 3),
        "midi_bpm": round(float(midi_tempo_bpm), 3) if midi_tempo_bpm is not None else None,
        "midi_meta": {
            "track_count": int(midi_info["track_count"]),
            "total_note_count": int(midi_info["total_note_count"]),
            "mapped_note_ratio": round(float(midi_info["mapped_ratio"]), 3),
            "malformed_note_count": int(midi_info["malformed_note_count"]),
        },
        "format_checks": format_checks,
        "element_comparison": element_rows,
        "recommendations": recommendations,
    }


def build_midi_quality_text_report(report: dict[str, Any]) -> str:
    """Render the MIDI quality report in plain text for copy/paste."""
    lines: list[str] = []
    lines.append("POST-RIP MIDI QUALITY REPORT")
    lines.append("=" * 28)
    lines.append(f"Overall score: {report['overall_score']:.3f} ({report['grade']})")
    lines.append(f"Reference BPM: {report['reference_bpm']}")
    lines.append(f"MIDI BPM: {report['midi_bpm'] if report['midi_bpm'] is not None else 'Not found'}")
    lines.append("")
    lines.append("Subscores:")
    for score_key, value in report["scores"].items():
        lines.append(f"- {score_key}: {value:.3f}")
    lines.append("")
    lines.append("Format checks:")
    for check in report["format_checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- [{marker}] {check['name']}: {check['details']}")

    if report["recommendations"]:
        lines.append("")
        lines.append("Recommended fixes:")
        for item in report["recommendations"]:
            lines.append(f"- {item}")

    lines.append("")
    lines.append("Element comparison:")
    for row in report["element_comparison"]:
        lines.append(
            "- "
            f"{row['element']} | score={row['element_score']:.3f} "
            f"coverage={row['coverage']:.3f} precision={row['precision']:.3f} "
            f"timing={row['timing_score']:.3f} density={row['density_score']:.3f}"
        )
    return "\n".join(lines)
