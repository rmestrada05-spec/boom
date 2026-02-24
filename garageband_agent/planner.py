"""Natural-language intent parsing and GarageBand action planning."""

from __future__ import annotations

import json
import re
from dataclasses import asdict

from .models import ActionPlan, ActionStep, PlaybackTarget, ProductionIntent

TEMPO_RE = re.compile(r"\b(?P<bpm>[4-9]\d|1\d\d|2[0-4]\d)\s*bpm\b", re.IGNORECASE)
ROOM_DIMS_RE = re.compile(
    r"(?P<length>\d+(?:\.\d+)?)\s*(?:ft|feet|m|meter|meters|')?\s*[x×]\s*"
    r"(?P<width>\d+(?:\.\d+)?)\s*(?:ft|feet|m|meter|meters|')?\s*[x×]\s*"
    r"(?P<height>\d+(?:\.\d+)?)\s*(?:ft|feet|m|meter|meters|')?",
    re.IGNORECASE,
)

GENRE_HINTS: dict[str, tuple[str, ...]] = {
    "gabber": ("gabber", "hardcore", "rotterdam", "hardstyle"),
    "lofi": ("lofi", "lo-fi", "chillhop", "boom bap"),
    "house": ("house", "four on the floor", "4 on the floor"),
    "trap": ("trap", "808", "drill"),
    "cinematic": ("cinematic", "film score", "trailer"),
}

INSTRUMENT_HINTS: dict[str, tuple[str, ...]] = {
    "bass": ("bass", "sub", "low end", "low-end"),
    "kick": ("kick", "drum", "drums"),
    "vocal": ("vocal", "voice", "singing"),
    "synth": ("synth", "lead", "pad", "arp"),
    "guitar": ("guitar", "amp", "strum"),
}

DESCRIPTOR_HINTS: dict[str, tuple[str, ...]] = {
    "warmer": ("warm", "warmer", "thicker"),
    "brighter": ("bright", "brighter", "sparkle"),
    "cleaner": ("clean", "cleaner", "less muddy", "de-mud"),
    "bigger": ("bigger", "larger", "wider", "huge"),
    "aggressive": ("aggressive", "harder", "punchier", "hit harder"),
}

CAR_HINTS = ("car", "jetta", "tdi", "sedan", "truck", "vehicle")
CLUB_HINTS = ("club", "venue", "room", "hall", "stage")
HEADPHONE_HINTS = ("headphone", "headphones", "earbuds", "iem", "airpods")


def parse_intent(prompt: str) -> ProductionIntent:
    """Extract structured production intent from plain language."""
    lowered = prompt.lower()

    tempo_match = TEMPO_RE.search(lowered)
    tempo_bpm = int(tempo_match.group("bpm")) if tempo_match else None

    genres = _match_tags(lowered, GENRE_HINTS)
    instruments = _match_tags(lowered, INSTRUMENT_HINTS)
    descriptors = _match_tags(lowered, DESCRIPTOR_HINTS)
    playback_targets = _extract_playback_targets(prompt, lowered)

    return ProductionIntent(
        raw_prompt=prompt,
        tempo_bpm=tempo_bpm,
        genres=tuple(genres),
        instruments=tuple(instruments),
        descriptors=tuple(descriptors),
        playback_targets=tuple(playback_targets),
    )


def build_action_plan(prompt: str) -> ActionPlan:
    """Parse prompt and build an ordered GarageBand action plan."""
    intent = parse_intent(prompt)
    steps: list[ActionStep] = []
    warnings: list[str] = []

    # Universal setup to make control locations understandable while learning.
    steps.append(
        ActionStep(
            title="Enable Quick Help while learning controls",
            instructions="Turn on Quick Help so hovering any button explains it.",
            why="Lets a taste-first producer learn controls without guesswork.",
            control_ids=("help_quick_help",),
        )
    )

    planned_tempo = intent.tempo_bpm
    if "gabber" in intent.genres and planned_tempo is None:
        planned_tempo = 160
        warnings.append("No tempo provided; defaulted gabber plan to 160 BPM.")

    if planned_tempo is not None:
        steps.append(
            ActionStep(
                title="Set project tempo",
                instructions=f"Set the project tempo to {planned_tempo} BPM in the LCD display.",
                why="Tempo anchors groove and genre feel before sound design.",
                control_ids=("lcd_tempo",),
                parameters={"tempo_bpm": str(planned_tempo)},
            )
        )

    steps.extend(_instrument_steps(intent, planned_tempo))
    steps.extend(_descriptor_steps(intent))
    steps.extend(_playback_translation_steps(intent))

    summary = _build_summary(intent, planned_tempo)
    return ActionPlan(
        summary=summary,
        intent=intent,
        steps=tuple(steps),
        warnings=tuple(warnings),
    )


def plan_to_pretty_text(plan: ActionPlan) -> str:
    """Render an action plan into a readable checklist."""
    lines = [f"Plan: {plan.summary}"]
    for index, step in enumerate(plan.steps, start=1):
        lines.append(f"{index}. {step.title}")
        lines.append(f"   - Do: {step.instructions}")
        lines.append(f"   - Why: {step.why}")
        if step.control_ids:
            lines.append(f"   - Controls: {', '.join(step.control_ids)}")
        if step.parameters:
            rendered_params = ", ".join(f"{k}={v}" for k, v in step.parameters.items())
            lines.append(f"   - Parameters: {rendered_params}")
    if plan.warnings:
        lines.append("Warnings:")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def plan_to_json(plan: ActionPlan) -> str:
    """Serialize a plan as formatted JSON for downstream automation."""
    return json.dumps(asdict(plan), indent=2)


def _instrument_steps(intent: ProductionIntent, tempo_bpm: int | None) -> list[ActionStep]:
    steps: list[ActionStep] = []
    wants_bass = "bass" in intent.instruments or "gabber" in intent.genres

    if wants_bass and "gabber" in intent.genres:
        target_tempo = tempo_bpm or 160
        steps.extend(_gabber_bass_steps(target_tempo))
    elif wants_bass:
        steps.extend(_generic_bass_steps())

    if "kick" in intent.instruments and "gabber" not in intent.genres:
        steps.append(
            ActionStep(
                title="Add a punchy kick layer",
                instructions="Create a drum track and program 4-on-the-floor kick hits.",
                why="Defines groove and leaves room for bass arrangement.",
                control_ids=("track_new", "step_sequencer_pattern", "note_velocity"),
            )
        )

    if not steps:
        steps.append(
            ActionStep(
                title="Create a starting instrument track",
                instructions=(
                    "Add a Software Instrument track, open Library, and choose a patch "
                    "that matches your prompt before editing tone."
                ),
                why="Gives the planner a concrete source to shape.",
                control_ids=("track_new", "library_toggle"),
            )
        )
    return steps


def _gabber_bass_steps(tempo_bpm: int) -> list[ActionStep]:
    return [
        ActionStep(
            title="Create gabber bass source track",
            instructions=(
                "Add a Software Instrument track, open Library, and choose an aggressive "
                "synth or distorted bass patch."
            ),
            why="Gabber bass needs a harmonically rich source, not a pure sine.",
            control_ids=("track_new", "library_toggle"),
            parameters={"style": "gabber_bass"},
        ),
        ActionStep(
            title="Program driving rhythm at gabber tempo",
            instructions=(
                f"Use Step Sequencer or Piano Roll to program 16th-note movement at {tempo_bpm} BPM "
                "with strong downbeat accents."
            ),
            why="Fast repetitive motion is core to a gabber feel.",
            control_ids=("editor_toggle", "step_sequencer_pattern", "note_velocity"),
            parameters={"grid": "1/16", "accent_pattern": "downbeats"},
        ),
        ActionStep(
            title="Add hardcore saturation",
            instructions=(
                "Insert Distortion or Overdrive and push drive until bass is clearly gritty "
                "without destroying note definition."
            ),
            why="Distortion creates the hard-edged character associated with gabber.",
            control_ids=("plugin_slot", "plugin_distortion", "plugin_overdrive"),
            parameters={"drive": "medium-high"},
        ),
        ActionStep(
            title="Shape low-end punch and control",
            instructions=(
                "Insert Channel EQ and Compressor. Boost around 50-70 Hz for impact, trim "
                "200-350 Hz if muddy, and compress with fast attack/release for consistency."
            ),
            why="Keeps bass heavy, aggressive, and controlled at high BPM.",
            control_ids=("plugin_channel_eq", "plugin_compressor"),
            parameters={"eq_focus": "50-70Hz", "mud_cut": "200-350Hz"},
        ),
        ActionStep(
            title="Build kick-bass lock",
            instructions=(
                "Add a drum/kick track and keep kick transient clear by reducing bass notes "
                "at exact kick hits or lightly automating bass volume dips."
            ),
            why="Kick and bass interaction determines how hard the track hits.",
            control_ids=("track_new", "automation_show"),
            parameters={"kick_pattern": "4-on-floor"},
        ),
    ]


def _generic_bass_steps() -> list[ActionStep]:
    return [
        ActionStep(
            title="Create bass instrument track",
            instructions="Add a Software Instrument track and choose a bass patch from Library.",
            why="Builds a bass foundation before tone shaping.",
            control_ids=("track_new", "library_toggle"),
        ),
        ActionStep(
            title="Set bass rhythm and velocity",
            instructions="Edit MIDI notes in Piano Roll and adjust velocity for groove.",
            why="Velocity variation keeps bass musical instead of robotic.",
            control_ids=("editor_toggle", "note_velocity"),
        ),
        ActionStep(
            title="Control bass tone",
            instructions="Use Channel EQ and Compressor to balance punch and clarity.",
            why="Makes bass translate better across different playback systems.",
            control_ids=("plugin_channel_eq", "plugin_compressor"),
        ),
    ]


def _descriptor_steps(intent: ProductionIntent) -> list[ActionStep]:
    steps: list[ActionStep] = []
    descriptors = set(intent.descriptors)

    if "warmer" in descriptors:
        steps.append(
            ActionStep(
                title="Warm the tonal balance",
                instructions=(
                    "Use EQ to add a gentle low-mid lift and soften harsh upper mids. "
                    "Optionally use Overdrive at low mix for harmonic warmth."
                ),
                why="Warmth usually comes from controlled low-mids plus soft harmonics.",
                control_ids=("plugin_channel_eq", "plugin_overdrive"),
            )
        )

    if "brighter" in descriptors:
        steps.append(
            ActionStep(
                title="Increase top-end clarity",
                instructions="Add a gentle high-shelf boost and reduce masking low-mids.",
                why="Brightness improves detail without needing excessive loudness.",
                control_ids=("plugin_channel_eq",),
            )
        )

    if "cleaner" in descriptors:
        steps.append(
            ActionStep(
                title="Clean muddy frequencies",
                instructions=(
                    "Cut problematic low-mids, tidy overlapping bass/kick ranges, and use "
                    "noise gate where appropriate on noisy audio tracks."
                ),
                why="Cleaning mud improves impact and translation.",
                control_ids=("plugin_channel_eq", "plugin_noise_gate"),
            )
        )

    if "bigger" in descriptors:
        steps.append(
            ActionStep(
                title="Make the section feel bigger",
                instructions=(
                    "Widen key layers with Chorus and automate reverb/echo sends during the "
                    "target section (for example, chorus only)."
                ),
                why="Width plus time-based automation creates perceived size.",
                control_ids=("plugin_chorus", "send_reverb", "send_echo", "automation_show"),
            )
        )

    if "aggressive" in descriptors:
        steps.append(
            ActionStep(
                title="Increase aggression",
                instructions=(
                    "Increase transient contrast with compression and add moderate saturation "
                    "on key rhythm elements."
                ),
                why="Aggression is mostly envelope control plus harmonics.",
                control_ids=("plugin_compressor", "plugin_distortion"),
            )
        )

    return steps


def _playback_translation_steps(intent: ProductionIntent) -> list[ActionStep]:
    steps: list[ActionStep] = []
    for target in intent.playback_targets:
        if target.target_type == "car":
            steps.append(
                ActionStep(
                    title="Create car translation pass",
                    instructions=(
                        "Duplicate the latest bounce, then focus sub impact around 45-70 Hz "
                        "and trim muddy resonance zones using narrow EQ cuts."
                    ),
                    why="Cars exaggerate some low frequencies and cancel others.",
                    control_ids=("plugin_channel_eq", "plugin_compressor", "share_export_song"),
                    parameters={"target": target.description},
                )
            )
        elif target.target_type == "club":
            dims = target.details.get("dimensions", "unknown dimensions")
            steps.append(
                ActionStep(
                    title="Create venue translation pass",
                    instructions=(
                        "Apply club-focused low-end management, keep kick transients controlled, "
                        "and export a dedicated venue version for soundcheck."
                    ),
                    why=f"Room modes and PA behavior depend heavily on venue size ({dims}).",
                    control_ids=("plugin_channel_eq", "plugin_limiter", "share_export_song"),
                    parameters={"venue": target.description},
                )
            )
        elif target.target_type == "headphones":
            steps.append(
                ActionStep(
                    title="Create headphone translation pass",
                    instructions=(
                        "Compare the mix on reference headphones, then adjust high-end harshness "
                        "and sub-bass balance so the mix still works on speakers."
                    ),
                    why="Headphones can overstate stereo width and hide room interaction issues.",
                    control_ids=("plugin_channel_eq", "plugin_compressor", "share_export_song"),
                    parameters={"headphones": target.description},
                )
            )
    return steps


def _build_summary(intent: ProductionIntent, planned_tempo: int | None) -> str:
    parts: list[str] = []
    if intent.genres:
        parts.append(f"style={', '.join(intent.genres)}")
    if intent.instruments:
        parts.append(f"instruments={', '.join(intent.instruments)}")
    if planned_tempo is not None:
        parts.append(f"tempo={planned_tempo} BPM")
    if intent.playback_targets:
        targets = ", ".join(target.target_type for target in intent.playback_targets)
        parts.append(f"translation targets={targets}")
    if not parts:
        return "General GarageBand production plan from natural-language prompt."
    return "GarageBand plan: " + "; ".join(parts)


def _match_tags(text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
    matched: list[str] = []
    for canonical, phrases in mapping.items():
        if any(phrase in text for phrase in phrases):
            matched.append(canonical)
    return matched


def _extract_playback_targets(prompt: str, lowered: str) -> list[PlaybackTarget]:
    targets: list[PlaybackTarget] = []
    if any(hint in lowered for hint in CAR_HINTS):
        car_match = re.search(r"\b(?:\d{4}\s+)?[a-z0-9\- ]*(jetta|civic|accord|camry)[a-z0-9\- ]*\b", lowered)
        car_name = car_match.group(0).strip() if car_match else "user vehicle"
        targets.append(PlaybackTarget(target_type="car", description=car_name))

    if any(hint in lowered for hint in CLUB_HINTS):
        dims_match = ROOM_DIMS_RE.search(prompt)
        details: dict[str, str] = {}
        if dims_match:
            dimensions = (
                f"{dims_match.group('length')}x{dims_match.group('width')}x"
                f"{dims_match.group('height')}"
            )
            details["dimensions"] = dimensions
            description = f"venue ({dimensions})"
        else:
            description = "venue"
        targets.append(PlaybackTarget(target_type="club", description=description, details=details))

    if any(hint in lowered for hint in HEADPHONE_HINTS):
        model = _extract_headphone_model(prompt)
        targets.append(
            PlaybackTarget(
                target_type="headphones",
                description=model or "headphones",
                details={"model": model or "unknown"},
            )
        )
    return targets


def _extract_headphone_model(prompt: str) -> str | None:
    # Grab text after "headphones" or "headphone" up to punctuation/connector.
    match = re.search(
        r"headphones?\s*(?:like|model|are|is|:)?\s*([A-Za-z0-9][A-Za-z0-9\-\s]{1,50})",
        prompt,
        re.IGNORECASE,
    )
    if not match:
        return None

    candidate = match.group(1).strip()
    # Stop at common connectors to avoid swallowing whole sentences.
    for stopper in (" and ", " but ", " so ", ",", ".", ";"):
        if stopper in candidate.lower():
            candidate = candidate[: candidate.lower().index(stopper)].strip()
    return candidate or None
