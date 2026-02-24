"""GarageBand controls and helper lookups.

The goal is to centralize button/menu knowledge so the planner can map
natural language ("make it warmer", "add gabber bass") to concrete UI steps.
"""

from __future__ import annotations

from collections import defaultdict

from .models import GarageBandControl


# This list is intentionally broad across transport, track, editor, plugin,
# and export surfaces. It can be extended without changing planner code.
GARAGEBAND_CONTROLS: tuple[GarageBandControl, ...] = (
    GarageBandControl(
        "transport_play",
        "Play",
        "Top transport bar",
        "Start playback from the playhead.",
        "Space",
        ("transport", "preview", "audition"),
    ),
    GarageBandControl(
        "transport_stop",
        "Stop",
        "Top transport bar",
        "Stop playback or recording.",
        "Space",
        ("transport", "halt"),
    ),
    GarageBandControl(
        "transport_record",
        "Record",
        "Top transport bar",
        "Record the armed track(s) at the playhead.",
        "R",
        ("record", "capture", "take"),
    ),
    GarageBandControl(
        "transport_cycle",
        "Cycle",
        "Top transport bar",
        "Loop playback/recording over selected cycle region.",
        "C",
        ("loop", "repeat"),
    ),
    GarageBandControl(
        "transport_metronome",
        "Metronome",
        "Top transport bar",
        "Toggle click track to monitor timing.",
        "K",
        ("click", "timing", "tempo"),
    ),
    GarageBandControl(
        "transport_count_in",
        "Count-in",
        "Top transport bar",
        "Add pre-roll clicks before recording starts.",
        "",
        ("pre-roll", "timing", "record"),
    ),
    GarageBandControl(
        "lcd_tempo",
        "Tempo display",
        "LCD display in transport bar",
        "Set project BPM.",
        "",
        ("bpm", "speed", "tempo"),
    ),
    GarageBandControl(
        "lcd_key_signature",
        "Key signature display",
        "LCD display in transport bar",
        "Set project key signature.",
        "",
        ("key", "scale", "tonality"),
    ),
    GarageBandControl(
        "lcd_time_signature",
        "Time signature display",
        "LCD display in transport bar",
        "Set beats per bar and note value.",
        "",
        ("meter", "signature", "rhythm"),
    ),
    GarageBandControl(
        "library_toggle",
        "Library",
        "Top-left panel toggle",
        "Open instrument and patch browser.",
        "Y",
        ("patch", "preset", "sound"),
    ),
    GarageBandControl(
        "smart_controls_toggle",
        "Smart Controls",
        "Bottom panel toggle",
        "Show macro controls for selected track patch.",
        "B",
        ("macros", "tone", "knobs"),
    ),
    GarageBandControl(
        "editor_toggle",
        "Editor",
        "Bottom panel toggle",
        "Open piano roll/audio editor/step sequencer for selected region.",
        "E",
        ("piano roll", "region", "edit"),
    ),
    GarageBandControl(
        "note_pad_toggle",
        "Notepad",
        "Top-right Notes button",
        "Store session notes and production instructions.",
        "",
        ("notes", "comments", "directions"),
    ),
    GarageBandControl(
        "track_new",
        "New Track",
        "Track menu or + button",
        "Create audio, software instrument, or drummer tracks.",
        "Option-Command-N",
        ("track", "add", "create"),
    ),
    GarageBandControl(
        "track_header_mute",
        "Mute",
        "Track header M button",
        "Silence selected track.",
        "",
        ("mute", "silence"),
    ),
    GarageBandControl(
        "track_header_solo",
        "Solo",
        "Track header S button",
        "Listen to only selected track(s).",
        "",
        ("solo", "isolate"),
    ),
    GarageBandControl(
        "track_header_record_enable",
        "Record Enable",
        "Track header red arm button",
        "Arm track for recording.",
        "",
        ("arm", "record"),
    ),
    GarageBandControl(
        "track_header_monitor",
        "Input Monitoring",
        "Track header monitoring button",
        "Hear incoming audio on selected track.",
        "",
        ("monitor", "input"),
    ),
    GarageBandControl(
        "track_volume",
        "Track Volume slider",
        "Track header",
        "Adjust track loudness.",
        "",
        ("gain", "level", "loud"),
    ),
    GarageBandControl(
        "track_pan",
        "Track Pan knob",
        "Track header",
        "Place track left/right in stereo image.",
        "",
        ("stereo", "left", "right"),
    ),
    GarageBandControl(
        "automation_show",
        "Show Automation",
        "Mix menu",
        "Display automation lanes for volume/pan/smart controls.",
        "A",
        ("automation", "ride", "envelope"),
    ),
    GarageBandControl(
        "automation_mode",
        "Automation mode",
        "Track header automation dropdown",
        "Choose Read/Touch/Latch automation behavior.",
        "",
        ("read", "touch", "latch"),
    ),
    GarageBandControl(
        "region_split",
        "Split Region at Playhead",
        "Edit menu",
        "Cut selected region at current playhead.",
        "Command-T",
        ("split", "slice", "cut"),
    ),
    GarageBandControl(
        "region_join",
        "Join Regions",
        "Edit menu",
        "Merge adjacent regions of same track/source.",
        "Command-J",
        ("join", "merge", "consolidate"),
    ),
    GarageBandControl(
        "region_loop",
        "Region Loop Handle",
        "Top-right edge of region",
        "Repeat selected region quickly.",
        "",
        ("loop", "repeat"),
    ),
    GarageBandControl(
        "quantize",
        "Quantize",
        "Editor > Region inspector",
        "Snap MIDI notes to rhythmic grid.",
        "",
        ("timing", "tight", "grid"),
    ),
    GarageBandControl(
        "note_velocity",
        "Velocity",
        "Piano roll note inspector",
        "Set MIDI note intensity/impact.",
        "",
        ("hard", "soft", "accent"),
    ),
    GarageBandControl(
        "step_sequencer_pattern",
        "Step Sequencer pattern",
        "Editor when a pattern region is selected",
        "Program rhythmic note triggers lane-by-lane.",
        "",
        ("step", "sequence", "pattern"),
    ),
    GarageBandControl(
        "plugin_slot",
        "Plug-ins & EQ slots",
        "Smart Controls > Inspector",
        "Insert or reorder audio effects.",
        "",
        ("effects", "plugin", "insert"),
    ),
    GarageBandControl(
        "plugin_channel_eq",
        "Channel EQ",
        "Plug-ins slot",
        "Shape tonal balance across frequencies.",
        "",
        ("eq", "brightness", "mud"),
    ),
    GarageBandControl(
        "plugin_compressor",
        "Compressor",
        "Plug-ins slot",
        "Control dynamic range and punch.",
        "",
        ("compression", "punch", "glue"),
    ),
    GarageBandControl(
        "plugin_noise_gate",
        "Noise Gate",
        "Plug-ins slot",
        "Reduce background noise between phrases.",
        "",
        ("gate", "noise"),
    ),
    GarageBandControl(
        "plugin_distortion",
        "Distortion",
        "Plug-ins slot",
        "Add aggressive harmonic saturation.",
        "",
        ("drive", "grit", "hardcore"),
    ),
    GarageBandControl(
        "plugin_overdrive",
        "Overdrive",
        "Plug-ins slot",
        "Add warmer clipping/saturation.",
        "",
        ("warmth", "drive"),
    ),
    GarageBandControl(
        "plugin_bitcrusher",
        "Bitcrusher",
        "Plug-ins slot",
        "Create lo-fi digital crunch.",
        "",
        ("lo-fi", "crusher", "digital"),
    ),
    GarageBandControl(
        "plugin_visual_eq",
        "Visual EQ",
        "Plug-ins slot",
        "Fast visual tonal shaping per track.",
        "",
        ("eq", "visual"),
    ),
    GarageBandControl(
        "plugin_chorus",
        "Chorus",
        "Plug-ins slot",
        "Widen and thicken sustained sounds.",
        "",
        ("width", "thick"),
    ),
    GarageBandControl(
        "plugin_limiter",
        "Limiter",
        "Plug-ins slot",
        "Cap peaks to avoid clipping.",
        "",
        ("ceiling", "loudness"),
    ),
    GarageBandControl(
        "send_reverb",
        "Track Reverb send",
        "Smart Controls > Master Effects",
        "Send track signal to project reverb bus.",
        "",
        ("space", "depth", "reverb"),
    ),
    GarageBandControl(
        "send_echo",
        "Track Echo send",
        "Smart Controls > Master Effects",
        "Send track signal to project echo bus.",
        "",
        ("delay", "echo"),
    ),
    GarageBandControl(
        "master_track_show",
        "Show Master Track",
        "Track menu",
        "Expose master bus for final processing/automation.",
        "",
        ("master", "bus", "final"),
    ),
    GarageBandControl(
        "master_volume",
        "Master Volume",
        "Master track or output controls",
        "Control final project output level.",
        "",
        ("output", "overall"),
    ),
    GarageBandControl(
        "master_pitch",
        "Master Pitch",
        "Control bar key/pitch settings",
        "Transpose entire project if needed.",
        "",
        ("transpose", "key shift"),
    ),
    GarageBandControl(
        "drummer_editor",
        "Drummer editor",
        "Bottom editor for drummer regions",
        "Set drummer style, complexity, fills and swing.",
        "",
        ("drums", "groove"),
    ),
    GarageBandControl(
        "sampler_editor",
        "Sampler controls",
        "Sampler track smart controls",
        "Shape ADSR/filter for sampled instruments.",
        "",
        ("attack", "release", "filter"),
    ),
    GarageBandControl(
        "tuner",
        "Tuner",
        "Track controls for audio instrument tracks",
        "Tune live instruments before recording.",
        "",
        ("tune", "pitch"),
    ),
    GarageBandControl(
        "countdown_in",
        "Countdown",
        "Record settings",
        "Specify bars/beats before recording punch-in.",
        "",
        ("count", "record prep"),
    ),
    GarageBandControl(
        "share_export_song",
        "Export Song to Disk",
        "Share menu",
        "Bounce project to audio file.",
        "",
        ("export", "bounce", "render"),
    ),
    GarageBandControl(
        "share_export_quality",
        "Export quality options",
        "Export dialog",
        "Pick format, bitrate, and project range for export.",
        "",
        ("mp3", "wav", "aac", "quality"),
    ),
    GarageBandControl(
        "help_quick_help",
        "Quick Help",
        "Help menu / question mark button",
        "Show inline descriptions for hovered controls.",
        "Shift-/",
        ("learn", "tooltip", "what does this do"),
    ),
)


CONTROLS_BY_ID: dict[str, GarageBandControl] = {
    control.control_id: control for control in GARAGEBAND_CONTROLS
}


def get_control(control_id: str) -> GarageBandControl | None:
    """Return a control by ID if present."""
    return CONTROLS_BY_ID.get(control_id)


def search_controls(query: str, limit: int = 20) -> list[GarageBandControl]:
    """Return controls ranked by relevance to the provided query."""
    cleaned = query.strip().lower()
    if not cleaned:
        return list(GARAGEBAND_CONTROLS[:limit])

    tokens = [token for token in cleaned.replace("/", " ").split() if token]
    if not tokens:
        return list(GARAGEBAND_CONTROLS[:limit])

    scores: dict[str, int] = defaultdict(int)
    for control in GARAGEBAND_CONTROLS:
        haystack = " ".join(
            [
                control.control_id,
                control.label,
                control.location,
                control.purpose,
                " ".join(control.keywords),
            ]
        ).lower()
        for token in tokens:
            if token in control.control_id:
                scores[control.control_id] += 6
            if token in control.label.lower():
                scores[control.control_id] += 5
            if token in control.purpose.lower():
                scores[control.control_id] += 3
            if token in control.location.lower():
                scores[control.control_id] += 2
            if token in haystack:
                scores[control.control_id] += 1

    ranked = sorted(
        GARAGEBAND_CONTROLS,
        key=lambda control: (-scores.get(control.control_id, 0), control.label),
    )
    return [control for control in ranked if scores.get(control.control_id, 0) > 0][:limit]
