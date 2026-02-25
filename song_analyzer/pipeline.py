"""High-level analysis pipeline with optional Demucs stem separation."""

from __future__ import annotations

from typing import Any

import numpy as np

from song_analyzer.analysis import analyze_song as analyze_mix_song
from song_analyzer.stem_separation import (
    DEFAULT_DEMUCS_MODEL,
    StemSeparationError,
    cleanup_stem_output,
    separate_stems_with_demucs,
)


ANALYSIS_MODE_MIX = "mix_heuristic"
ANALYSIS_MODE_STEM = "stem_separated"

STEM_TO_ELEMENT_KEYS: dict[str, tuple[str, ...]] = {
    "drums": (
        "kick",
        "snare_clap",
        "hihat_rolls",
        "percussion_secondary",
        "transitions_fills",
        "impacts_hits",
    ),
    "bass": (
        "bass_808_sub",
        "bass_midrange",
        "counter_808s",
        "reese_bass",
    ),
    "vocals": (
        "main_vocals",
        "adlibs",
        "vocal_chops",
        "vocal_fx_processing",
        "vocal_one_shots",
    ),
    "other": (
        "lead_synth_melody",
        "chords_pads",
        "counter_melody",
        "synth_brass_stabs",
        "risers",
        "sweeps_downlifters",
        "white_noise_sweeps",
        "foley_sfx",
        "atmospheres_textures",
        "growls_screeches",
        "plucks",
        "supersaw",
    ),
    "guitar": (
        "lead_synth_melody",
        "counter_melody",
        "chords_pads",
    ),
    "piano": (
        "lead_synth_melody",
        "counter_melody",
        "chords_pads",
        "plucks",
    ),
}


def _with_source(detections: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for detection in detections:
        cloned = dict(detection)
        cloned["analysis_source"] = source
        output.append(cloned)
    return output


def _select_element_keys(
    detections: list[dict[str, Any]],
    allowed_keys: tuple[str, ...],
    source: str,
) -> list[dict[str, Any]]:
    allowed_set = set(allowed_keys)
    output: list[dict[str, Any]] = []
    for detection in detections:
        if detection["element_key"] not in allowed_set:
            continue
        cloned = dict(detection)
        # Stem-isolated detections are generally more reliable for timing.
        cloned["confidence"] = round(float(min(1.0, (float(cloned["confidence"]) * 1.08))), 3)
        cloned["analysis_source"] = source
        output.append(cloned)
    return output


def _merge_stem_and_mix_detections(
    mix_detections: list[dict[str, Any]],
    stem_detections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not stem_detections:
        return mix_detections

    stem_keys = {item["element_key"] for item in stem_detections}
    fallback_mix = []
    for item in mix_detections:
        if item["element_key"] not in stem_keys:
            cloned = dict(item)
            cloned["analysis_source"] = "mix:fallback"
            fallback_mix.append(cloned)

    combined = stem_detections + fallback_mix
    combined.sort(key=lambda row: (row["start_seconds"], -row["confidence"]))
    return combined


def analyze_song(
    file_path: str,
    subgenre_profile: str = "General EDM-rap",
    analysis_mode: str = ANALYSIS_MODE_STEM,
    demucs_model: str = DEFAULT_DEMUCS_MODEL,
    strict_stem_mode: bool = False,
) -> dict[str, Any]:
    """Analyze song with optional AI stem separation refinement."""
    mix_result = analyze_mix_song(file_path=file_path, subgenre_profile=subgenre_profile)
    mix_detections = _with_source(mix_result["detections"], "mix")
    base_notes = [
        note
        for note in mix_result.get("notes", [])
        if "heuristic" not in str(note).lower()
    ]

    base_result = dict(mix_result)
    base_result["analysis_mode_requested"] = analysis_mode
    base_result["analysis_mode"] = ANALYSIS_MODE_MIX
    base_result["stem_separation_used"] = False
    base_result["demucs_model"] = None
    base_result["detections"] = mix_detections
    base_result["notes"] = base_notes

    if analysis_mode != ANALYSIS_MODE_STEM:
        base_result["notes"] = list(base_result.get("notes", [])) + [
            "Running in fast mix-only mode (no AI stem separation).",
        ]
        return base_result

    try:
        separation = separate_stems_with_demucs(file_path, model=demucs_model)
    except StemSeparationError as exc:
        if strict_stem_mode:
            raise ValueError(
                "AI stem separation failed. Install Demucs and ffmpeg, then retry. "
                f"Details: {exc}"
            ) from exc
        base_result["notes"] = list(base_result.get("notes", [])) + [
            "AI stem-separated mode requested, but stem extraction failed. "
            f"Falling back to mix-only analysis. Details: {exc}",
        ]
        return base_result

    stem_detections: list[dict[str, Any]] = []
    try:
        for stem_name, stem_path in separation.stems.items():
            allowed = STEM_TO_ELEMENT_KEYS.get(stem_name, ())
            if not allowed:
                continue
            stem_result = analyze_mix_song(file_path=stem_path, subgenre_profile=subgenre_profile)
            chosen = _select_element_keys(
                detections=stem_result["detections"],
                allowed_keys=allowed,
                source=f"stem:{stem_name}",
            )
            stem_detections.extend(chosen)
    finally:
        cleanup_stem_output(separation.output_root)

    combined_detections = _merge_stem_and_mix_detections(mix_detections, stem_detections)
    average_confidence = (
        float(np.mean([float(item["confidence"]) for item in combined_detections]))
        if combined_detections
        else 0.0
    )
    active_sources = sorted({item.get("analysis_source", "unknown") for item in combined_detections})

    result = dict(base_result)
    result["analysis_mode"] = ANALYSIS_MODE_STEM
    result["stem_separation_used"] = bool(stem_detections)
    result["demucs_model"] = demucs_model
    result["overall_detection_confidence"] = round(average_confidence, 3)
    result["detections"] = combined_detections
    result["notes"] = list(base_result.get("notes", [])) + [
        "AI stem-separated pipeline enabled (Demucs).",
        (
            "Source blend: "
            + (", ".join(active_sources) if active_sources else "mix-only fallback")
            + "."
        ),
        "Exact mathematical stem separation from a mixed master is not physically guaranteed, "
        "but this is significantly closer than mix-only heuristics.",
    ]
    return result
