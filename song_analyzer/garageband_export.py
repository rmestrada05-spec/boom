"""Export helpers for GarageBand-ready reconstruction assets."""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo


DEFAULT_BPM = 140.0
DEFAULT_TICKS_PER_BEAT = 480
MIN_NOTE_TICKS = 60


ELEMENT_MIDI_NOTE: dict[str, int] = {
    "kick": 36,
    "bass_808_sub": 35,
    "bass_midrange": 40,
    "snare_clap": 38,
    "hihat_rolls": 42,
    "percussion_secondary": 46,
    "lead_synth_melody": 72,
    "chords_pads": 65,
    "counter_melody": 76,
    "synth_brass_stabs": 70,
    "main_vocals": 69,
    "adlibs": 73,
    "vocal_chops": 74,
    "vocal_fx_processing": 71,
    "risers": 84,
    "impacts_hits": 49,
    "sweeps_downlifters": 83,
    "white_noise_sweeps": 81,
    "foley_sfx": 52,
    "transitions_fills": 47,
    "atmospheres_textures": 67,
    "growls_screeches": 54,
    "counter_808s": 41,
    "reese_bass": 43,
    "plucks": 79,
    "supersaw": 77,
    "vocal_one_shots": 75,
}


def _safe_bpm(bpm: float | int | None) -> float:
    try:
        if bpm is None:
            return DEFAULT_BPM
        parsed = float(bpm)
    except (TypeError, ValueError):
        return DEFAULT_BPM
    if parsed <= 0:
        return DEFAULT_BPM
    return parsed


def _seconds_to_ticks(seconds: float, bpm: float, ticks_per_beat: int = DEFAULT_TICKS_PER_BEAT) -> int:
    ticks_per_second = ticks_per_beat * (bpm / 60.0)
    return int(round(max(seconds, 0.0) * ticks_per_second))


def build_garageband_blueprint_midi(
    detections: list[dict[str, Any]],
    bpm: float,
    ticks_per_beat: int = DEFAULT_TICKS_PER_BEAT,
) -> bytes:
    """Return MIDI bytes representing detected arrangement lanes for GarageBand import."""
    effective_bpm = _safe_bpm(bpm)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for detection in detections:
        grouped[detection["element_key"]].append(detection)

    midi = MidiFile(type=1, ticks_per_beat=ticks_per_beat)

    tempo_track = MidiTrack()
    tempo_track.append(MetaMessage("track_name", name="Song Blueprint Tempo", time=0))
    tempo_track.append(MetaMessage("set_tempo", tempo=bpm2tempo(effective_bpm), time=0))
    tempo_track.append(MetaMessage("end_of_track", time=1))
    midi.tracks.append(tempo_track)

    for track_index, (element_key, element_detections) in enumerate(grouped.items()):
        element_detections.sort(key=lambda item: (item["start_seconds"], item["end_seconds"]))
        first = element_detections[0]

        track = MidiTrack()
        track_name = f"{first['element']} | {first['garageband_patch']}"
        track.append(MetaMessage("track_name", name=track_name[:127], time=0))

        channel = track_index % 16
        note = ELEMENT_MIDI_NOTE.get(element_key, 60)
        current_tick = 0

        for detection in element_detections:
            start_tick = _seconds_to_ticks(float(detection["start_seconds"]), effective_bpm, ticks_per_beat)
            end_tick = _seconds_to_ticks(float(detection["end_seconds"]), effective_bpm, ticks_per_beat)
            if start_tick < current_tick:
                start_tick = current_tick
            if end_tick <= start_tick:
                end_tick = start_tick + MIN_NOTE_TICKS
            velocity = int(max(32, min(127, round(float(detection["confidence"]) * 100))))

            track.append(
                Message(
                    "note_on",
                    note=note,
                    velocity=velocity,
                    channel=channel,
                    time=start_tick - current_tick,
                )
            )
            track.append(
                Message(
                    "note_off",
                    note=note,
                    velocity=0,
                    channel=channel,
                    time=end_tick - start_tick,
                )
            )
            current_tick = end_tick

        track.append(MetaMessage("end_of_track", time=1))
        midi.tracks.append(track)

    output = BytesIO()
    midi.save(file=output)
    return output.getvalue()


def build_garageband_blueprint_text(result: dict[str, Any], max_regions_per_element: int = 20) -> str:
    """Return a copy/paste production blueprint text for manual GarageBand recreation."""
    bpm = _safe_bpm(result.get("bpm"))
    detections = list(result.get("detections", []))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for detection in detections:
        grouped[detection["element_key"]].append(detection)

    lines: list[str] = []
    lines.append("GARAGEBAND REBUILD BLUEPRINT")
    lines.append("=" * 32)
    lines.append(f"Project tempo: {bpm:.2f} BPM")
    lines.append(f"Subgenre profile: {result.get('subgenre_profile', 'Unknown')}")
    lines.append(f"Detected layers: {len(detections)}")
    lines.append("")
    lines.append("SETUP STEPS")
    lines.append("1) Set GarageBand project tempo to detected BPM.")
    lines.append("2) Drag your reference song onto a muted audio track.")
    lines.append("3) Import the companion MIDI blueprint file from this app.")
    lines.append("4) Rename/replace each MIDI track with the suggested patch and FX chain.")
    lines.append("5) Use the timestamp regions below as your arrangement guide.")

    if not grouped:
        lines.append("")
        lines.append("No detectable layers met confidence thresholds.")
        return "\n".join(lines)

    for element_key, element_detections in grouped.items():
        element_detections.sort(key=lambda item: (item["start_seconds"], item["end_seconds"]))
        first = element_detections[0]
        lines.append("")
        lines.append(f"[Track] {first['element']}")
        lines.append(f"Patch: {first['garageband_patch']}")
        lines.append(f"Similar Sound: {first['garageband_similar_sound']}")
        lines.append(f"FX: {' | '.join(first['suggested_effects'])}")
        lines.append(f"Notes: {first['recreation_notes']}")
        lines.append("Regions:")

        for detection in element_detections[:max_regions_per_element]:
            lines.append(
                "  - "
                f"{detection['start_timestamp']} -> {detection['end_timestamp']} "
                f"(conf {detection['confidence']:.2f})"
            )

        remaining = len(element_detections) - max_regions_per_element
        if remaining > 0:
            lines.append(f"  - ... {remaining} more regions omitted for readability")

    return "\n".join(lines)


def build_garageband_blueprint_tsv(detections: list[dict[str, Any]]) -> str:
    """Return a tab-separated table that can be pasted into Notes/spreadsheets."""
    header = [
        "element",
        "start_timestamp",
        "end_timestamp",
        "confidence",
        "garageband_patch",
        "garageband_similar_sound",
        "suggested_effects",
        "recreation_notes",
    ]
    rows = ["\t".join(header)]
    for detection in detections:
        rows.append(
            "\t".join(
                [
                    str(detection["element"]),
                    str(detection["start_timestamp"]),
                    str(detection["end_timestamp"]),
                    f"{float(detection['confidence']):.3f}",
                    str(detection["garageband_patch"]).replace("\t", " "),
                    str(detection["garageband_similar_sound"]).replace("\t", " "),
                    " | ".join(detection["suggested_effects"]).replace("\t", " "),
                    str(detection["recreation_notes"]).replace("\t", " "),
                ]
            )
        )
    return "\n".join(rows)
