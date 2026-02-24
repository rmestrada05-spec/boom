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
python -m garageband_agent "add a bass sound at 160bpm to have a gabber feel to the track"
```

### List controls

```bash
python -m garageband_agent --list-controls
python -m garageband_agent --list-controls "automation"
```

### Show a single control

```bash
python -m garageband_agent --show-control plugin_channel_eq
```

### JSON output (for automation)

```bash
python -m garageband_agent --json "tune for my 2011 Jetta TDI and club 80x45x16 ft"
```

## Running tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Notes

- This project outputs a structured plan and control mapping; it does not yet
  drive GarageBand UI automatically.
- The control knowledge base can be expanded with more detailed, versioned
  GarageBand mappings over time.