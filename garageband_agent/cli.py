"""CLI entry point for the GarageBand director."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .knowledge_base import GARAGEBAND_CONTROLS, get_control, search_controls
from .planner import build_action_plan, plan_to_json, plan_to_pretty_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="garageband-agent",
        description=(
            "Translate natural-language production requests into concrete "
            "GarageBand control actions."
        ),
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Natural-language request (for example: 'add gabber bass at 160bpm').",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output plans as JSON instead of readable checklist text.",
    )
    parser.add_argument(
        "--list-controls",
        nargs="?",
        const="",
        default=None,
        help="List known GarageBand controls, optionally filtered by query.",
    )
    parser.add_argument(
        "--show-control",
        default=None,
        help="Show detailed info for a single control by control_id.",
    )
    return parser


def _print_controls(query: str, as_json: bool) -> int:
    controls = search_controls(query) if query else list(GARAGEBAND_CONTROLS)
    if as_json:
        print(json.dumps([asdict(control) for control in controls], indent=2))
    else:
        for control in controls:
            shortcut = f" [{control.shortcut}]" if control.shortcut else ""
            print(f"- {control.control_id}: {control.label}{shortcut}")
            print(f"  location: {control.location}")
            print(f"  purpose:  {control.purpose}")
            if control.keywords:
                print(f"  keywords: {', '.join(control.keywords)}")
    return 0


def _print_control(control_id: str, as_json: bool) -> int:
    control = get_control(control_id)
    if control is None:
        print(f"Unknown control_id: {control_id}", file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps(asdict(control), indent=2))
    else:
        print(f"{control.control_id}: {control.label}")
        print(f"location: {control.location}")
        print(f"purpose:  {control.purpose}")
        if control.shortcut:
            print(f"shortcut: {control.shortcut}")
        if control.keywords:
            print(f"keywords: {', '.join(control.keywords)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_controls is not None:
        return _print_controls(args.list_controls, args.json)
    if args.show_control:
        return _print_control(args.show_control, args.json)

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        parser.print_help()
        return 1

    plan = build_action_plan(prompt)
    if args.json:
        print(plan_to_json(plan))
    else:
        print(plan_to_pretty_text(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
