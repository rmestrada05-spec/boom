# GarageBand Taste Director (MVP)

This repository contains a lightweight "taste-first" GarageBand assistant.

It is designed for producers who can describe outcomes in plain language
("make this gabber at 160 BPM", "hit harder in my Jetta", "club translation")
and want concrete, button-level action plans in GarageBand.

## What it includes

- A GarageBand control knowledge base (`garageband_agent/knowledge_base.py`)
- A natural-language intent parser (`garageband_agent/planner.py`)
- A plan generator that maps requests to actionable steps
- A CLI for quick use from terminal
- Tests for parsing and control lookup

## Quick start

```bash
python3 -m garageband_agent "add a bass sound at 160bpm to have a gabber feel to the track"
```

### List controls

```bash
python3 -m garageband_agent --list-controls
python3 -m garageband_agent --list-controls "automation"
```

### Show a single control

```bash
python3 -m garageband_agent --show-control plugin_channel_eq
```

### JSON output (for automation)

```bash
python3 -m garageband_agent --json "tune for my 2011 Jetta TDI and club 80x45x16 ft"
```

### Analyze an uploaded song recording

```bash
# Readable summary
python3 -m garageband_agent --analyze-file "/path/to/song.wav"

# Machine-readable output
python3 -m garageband_agent --analyze-file "/path/to/song.wav" --json
```

### Split timestamped sounds into a cache for GarageBand

```bash
# Extract default event types into .garageband_cache/clips
python3 -m garageband_agent --split-file "/path/to/song.wav"

# Extract only bass + lead vocals
python3 -m garageband_agent \
  --split-file "/path/to/song.wav" \
  --split-event-types "bass_hits,lead_vocal_entries"

# List cached clips to quickly reuse in new projects
python3 -m garageband_agent --list-cache
```

Each split run writes:
- `CACHE_DIR/clips/*.wav` (default is 48 kHz, 24-bit WAV)
- `CACHE_DIR/index.json` (clip metadata cache)
- `CACHE_DIR/import_manifest.txt` (Finder/open instructions for GarageBand drag-drop)

## Running tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## Notes

- This project outputs a structured plan and control mapping; it does not yet
  drive GarageBand UI automatically.
- The control knowledge base can be expanded with more detailed, versioned
  GarageBand mappings over time.
- Song analysis labels are heuristic estimates with confidence scores; they are
  meant to speed creative review, not replace full stem-level transcription.
- WAV input is supported out of the box. For MP3/AAC and other formats, install
  `librosa` in your environment.
- Split extraction uses heuristic source enhancement (`clean_4k` profile): HPSS,
  spectral denoise gating, and tonal cleanup for cleaner pulls with less mud.