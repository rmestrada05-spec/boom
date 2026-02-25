"""GarageBand sound/effect suggestions for detected song elements."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GarageBandPreset:
    """Closest stock GarageBand sound plus an effects chain."""

    similar_sound: str
    patch: str
    effects: tuple[str, ...]
    recreation_notes: str


DEFAULT_PRESET = GarageBandPreset(
    similar_sound="Electronic > Synthesizer > Basic Analog",
    patch="Basic Analog",
    effects=(
        "Channel EQ (clean low-end and remove muddy 200-400 Hz)",
        "Compressor (glue dynamics)",
    ),
    recreation_notes="Start from a neutral synth and shape to taste with EQ + compression.",
)


ELEMENT_PRESETS: dict[str, GarageBandPreset] = {
    "kick": GarageBandPreset(
        similar_sound="Drum Kit Designer > SoCal / Trap-style kick sample",
        patch="SoCal Kit - Kick",
        effects=(
            "Channel EQ (+2 to +4 dB around 55-70 Hz, slight cut near 300 Hz)",
            "Compressor (fast attack, medium release)",
            "Overdrive (very light, 5-10% mix)",
        ),
        recreation_notes="Layer a short punch kick over a tuned low-end body if needed.",
    ),
    "bass_808_sub": GarageBandPreset(
        similar_sound="Bass > 808 Flex / Sub Bass",
        patch="808 Flex Bass",
        effects=(
            "Distortion (soft clip for harmonics)",
            "Channel EQ (high-cut around 7-10 kHz, boost 40-80 Hz carefully)",
            "Compressor (slow attack, medium release)",
            "Pitch automation or note glide (for slides)",
        ),
        recreation_notes="Use long notes with glide and tune the root note of each phrase.",
    ),
    "bass_midrange": GarageBandPreset(
        similar_sound="Bass > Growl Bass / Dirty Bass",
        patch="Dirty Synth Bass",
        effects=(
            "Bitcrusher or Distortion (moderate)",
            "Channel EQ (boost 150-400 Hz for weight, 1-2 kHz for bite)",
            "Compressor (parallel style if possible)",
        ),
        recreation_notes="Blend with 808 sub so this layer fills mids without overpowering lows.",
    ),
    "snare_clap": GarageBandPreset(
        similar_sound="Drum Machine Designer > Trap snare + clap layer",
        patch="Trap Snare Layer",
        effects=(
            "Channel EQ (body around 180-220 Hz, snap around 2-5 kHz)",
            "Space Designer / PlatinumVerb (short plate, low mix)",
            "Transient shaping via compression (fast attack/release)",
        ),
        recreation_notes="Layer a dry snare with a bright clap; keep timing very tight.",
    ),
    "hihat_rolls": GarageBandPreset(
        similar_sound="Drum Machine Designer > Closed/Open Hat samples",
        patch="Trap Hats",
        effects=(
            "Channel EQ (high-pass 200-300 Hz, add air at 8-12 kHz)",
            "Stereo delay (subtle ping-pong for movement)",
            "Auto filter or pan automation on rolls",
        ),
        recreation_notes="Program 1/16, triplet, and 1/32 rolls with velocity variation.",
    ),
    "percussion_secondary": GarageBandPreset(
        similar_sound="Electronic Percussion > Shaker/Rim/Tamb loops",
        patch="Electronic Perc Layer",
        effects=(
            "Channel EQ (carve space against hats and snare)",
            "Short room reverb",
            "Transient shaping with light compression",
        ),
        recreation_notes="Use call-and-response patterns against the main hat groove.",
    ),
    "lead_synth_melody": GarageBandPreset(
        similar_sound="Synthesizer > Bright Lead / FM Lead",
        patch="Aggressive FM Lead",
        effects=(
            "Chorus (subtle width)",
            "Delay (1/8 or dotted 1/8 tempo-synced)",
            "Reverb (small to medium hall)",
            "Saturation (light)",
        ),
        recreation_notes="Use a memorable 1-2 bar motif and automate filter cutoff in sections.",
    ),
    "chords_pads": GarageBandPreset(
        similar_sound="Synthesizer > Dream Pad / Airy Chords",
        patch="Dream Pad",
        effects=(
            "Stereo chorus",
            "Hall reverb (long tail)",
            "Channel EQ (high-pass around 120-200 Hz)",
        ),
        recreation_notes="Keep pads wide and soft so vocals and leads stay forward.",
    ),
    "counter_melody": GarageBandPreset(
        similar_sound="Synthesizer > Bell Pluck / Arp Pluck",
        patch="Bell Pluck",
        effects=(
            "Delay (tempo synced)",
            "Reverb throw on phrase endings",
            "EQ notch where lead sits",
        ),
        recreation_notes="Make this layer rhythmic and sparse; avoid clashing with main melody.",
    ),
    "synth_brass_stabs": GarageBandPreset(
        similar_sound="Synthesizer > Brass Stab",
        patch="Power Brass",
        effects=(
            "Compressor (to keep hits consistent)",
            "Saturation / Overdrive (light)",
            "Short room reverb",
        ),
        recreation_notes="Use short staccato MIDI notes and accent section transitions.",
    ),
    "main_vocals": GarageBandPreset(
        similar_sound="Vocal Track > Clean Modern Rap Vocal",
        patch="Modern Rap Vocal Chain",
        effects=(
            "Pitch correction (retune speed medium-fast)",
            "Compressor (2-stage if possible, total 4-8 dB gain reduction)",
            "Channel EQ (HPF 80-120 Hz, presence boost 3-6 kHz, air shelf 10+ kHz)",
            "De-esser (5-8 kHz control)",
            "Reverb (short plate) + Delay (slap or 1/8 throw)",
        ),
        recreation_notes="Record dry and stack doubles/ad-libs for width and energy.",
    ),
    "adlibs": GarageBandPreset(
        similar_sound="Vocal Track > Hype Ad-lib Layer",
        patch="Ad-lib Shout FX",
        effects=(
            "Pitch shift (+/- 3 to 7 semitones on duplicates)",
            "Distortion / Saturation (moderate)",
            "Heavy delay throws (1/4 or dotted 1/8)",
            "Longer reverb than lead vocal",
        ),
        recreation_notes="Pan ad-libs left/right and automate volume for callouts.",
    ),
    "vocal_chops": GarageBandPreset(
        similar_sound="Sampler > Vocal Chop Instrument",
        patch="Vocal Chop Sampler",
        effects=(
            "Flex pitch/time slicing in sampler",
            "Formant shift (Vocal Transformer)",
            "Gate or stutter via automation",
            "Reverb + delay for musical texture",
        ),
        recreation_notes="Slice syllables rhythmically and tune to song key/chord tones.",
    ),
    "vocal_fx_processing": GarageBandPreset(
        similar_sound="Vocal Transformer / Telephone FX Chain",
        patch="Processed Vocal FX",
        effects=(
            "Vocal Transformer (formant + pitch shift)",
            "Distortion or Bitcrusher",
            "Band-pass EQ (for radio/lo-fi moments)",
            "Large reverb for transitions",
        ),
        recreation_notes="Use this as an ear-candy layer, not a constant full-time effect.",
    ),
    "risers": GarageBandPreset(
        similar_sound="FX > Noise Riser",
        patch="White Noise Riser",
        effects=(
            "Auto filter (cutoff automation rising)",
            "Pitch automation upward",
            "Reverb and stereo widening",
        ),
        recreation_notes="Build 1-4 bars into major transitions or drops.",
    ),
    "impacts_hits": GarageBandPreset(
        similar_sound="FX > Impact Hit / Sub Drop",
        patch="Cinematic Impact",
        effects=(
            "Transient emphasis (compression)",
            "Layered sub drop",
            "Reverb tail for size",
        ),
        recreation_notes="Place impacts at drop starts and section boundaries.",
    ),
    "sweeps_downlifters": GarageBandPreset(
        similar_sound="FX > Downlifter Sweep",
        patch="Reverse Down Sweep",
        effects=(
            "Pitch automation downward",
            "Filter automation low-pass",
            "Reverb tail",
        ),
        recreation_notes="Use to release tension after fills and heavy hits.",
    ),
    "white_noise_sweeps": GarageBandPreset(
        similar_sound="FX > White Noise Sweep",
        patch="Noise Sweep",
        effects=(
            "High-pass/low-pass automation",
            "Stereo spread",
            "Short reverb",
        ),
        recreation_notes="Layer quietly behind risers for transition energy.",
    ),
    "foley_sfx": GarageBandPreset(
        similar_sound="Sampler > One-shot FX (gun, glass, reverse textures)",
        patch="FX One-shots",
        effects=(
            "Pitch shifting for variation",
            "Transient shaping",
            "Delay throws for ear candy",
        ),
        recreation_notes="Use sparingly as punctuation around bars and vocal phrases.",
    ),
    "transitions_fills": GarageBandPreset(
        similar_sound="Drummer / Drum Machine fills + reverse snare",
        patch="Trap Fill Layer",
        effects=(
            "Reverse sample processing",
            "Filter sweeps",
            "Short delay/reverb tail",
        ),
        recreation_notes="Use 1/2 bar and 1 bar fills to announce section changes.",
    ),
    "atmospheres_textures": GarageBandPreset(
        similar_sound="Synthesizer > Ambient Bed / Noise Texture",
        patch="Ambient Bed",
        effects=(
            "Long hall reverb",
            "Auto-pan very slow",
            "EQ dip in vocal midrange area",
        ),
        recreation_notes="Keep level low so texture is felt more than heard.",
    ),
    "growls_screeches": GarageBandPreset(
        similar_sound="Synthesizer > Aggro Growl / Distorted Lead",
        patch="Rage Growl",
        effects=(
            "Distortion/Overdrive (heavy)",
            "Multiband-style EQ moves (manual EQ in GarageBand)",
            "Automation on filter and resonance",
        ),
        recreation_notes="Automate movement each bar so growls feel alive.",
    ),
    "counter_808s": GarageBandPreset(
        similar_sound="Bass > Distorted 808 Layer",
        patch="Distorted 808 Layer",
        effects=(
            "Parallel distortion",
            "EQ separation from main 808",
            "Sidechain-like ducking against kick",
        ),
        recreation_notes="Blend low in mix to add aggression without muddying sub.",
    ),
    "reese_bass": GarageBandPreset(
        similar_sound="Synthesizer > Reese Bass",
        patch="Wide Reese",
        effects=(
            "Unison detune",
            "Chorus for width",
            "Low-pass automation",
        ),
        recreation_notes="Use in drops for a classic EDM low-mid wobble layer.",
    ),
    "plucks": GarageBandPreset(
        similar_sound="Synthesizer > Digital Pluck",
        patch="Glass Pluck",
        effects=(
            "Delay (tempo synced)",
            "Short reverb",
            "Transient-friendly compression",
        ),
        recreation_notes="Keep envelope short and rhythmic for bounce.",
    ),
    "supersaw": GarageBandPreset(
        similar_sound="Synthesizer > Supersaw Stack",
        patch="Festival Supersaw",
        effects=(
            "Unison detune/widening",
            "High-pass EQ to avoid low-end buildup",
            "Sidechain-style pump automation",
        ),
        recreation_notes="Layer octaves and keep chord voicing simple and wide.",
    ),
    "vocal_one_shots": GarageBandPreset(
        similar_sound="Sampler > Vocal One-shot Trigger",
        patch="Vocal Hit Trigger",
        effects=(
            "Pitch shift for key matching",
            "Short delay throw",
            "Reverb with filtered tail",
        ),
        recreation_notes="Trigger single words as rhythmic accents between bars.",
    ),
}


def get_preset_for_element(element_key: str) -> GarageBandPreset:
    """Return the closest GarageBand preset and FX chain for a detected element."""
    return ELEMENT_PRESETS.get(element_key, DEFAULT_PRESET)
