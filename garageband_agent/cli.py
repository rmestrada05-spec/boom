"""CLI entry point for the GarageBand director."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .knowledge_base import GARAGEBAND_CONTROLS, get_control, search_controls
from .live_agent import (
    AppleScriptController,
    LiveGarageBandAgent,
    live_report_to_pretty_text,
    run_live_agent_loop,
)
from .planner import build_action_plan, plan_to_json, plan_to_pretty_text
from .song_analyzer import analyze_song, analysis_to_json, analysis_to_pretty_text
from .splitter import (
    cached_clips_to_json,
    cached_clips_to_pretty_text,
    list_cached_clips,
    split_song_to_cache,
    splitter_report_to_json,
    splitter_report_to_pretty_text,
)


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
    parser.add_argument(
        "--analyze-file",
        default=None,
        help="Analyze an uploaded audio file and return BPM + timestamped events.",
    )
    parser.add_argument(
        "--max-analysis-preview",
        type=int,
        default=20,
        help="When not using --json, max timestamps previewed per event type.",
    )
    parser.add_argument(
        "--split-file",
        default=None,
        help=(
            "Split an uploaded song into cleaner timestamped clips and store "
            "them in cache for GarageBand import."
        ),
    )
    parser.add_argument(
        "--split-event-types",
        default="",
        help=(
            "Comma-separated event types to split (for example: "
            "bass_hits,synth_hits,lead_vocal_entries). "
            "If omitted, default split targets are used."
        ),
    )
    parser.add_argument(
        "--split-max-per-type",
        type=int,
        default=12,
        help="Max extracted clips per event type when splitting.",
    )
    parser.add_argument(
        "--split-min-confidence",
        type=float,
        default=0.45,
        help="Minimum event confidence threshold for splitting clips.",
    )
    parser.add_argument(
        "--split-pre-roll",
        type=float,
        default=0.08,
        help="Seconds before each timestamp to include in extracted clips.",
    )
    parser.add_argument(
        "--split-post-roll",
        type=float,
        default=0.90,
        help="Seconds after each timestamp to include in extracted clips.",
    )
    parser.add_argument(
        "--cache-dir",
        default=".garageband_cache",
        help="Cache directory used for split clip storage and manifests.",
    )
    parser.add_argument(
        "--list-cache",
        action="store_true",
        help="List cached clips currently stored in --cache-dir.",
    )
    parser.add_argument(
        "--cache-event-type",
        default=None,
        help="Optional cache event-type filter used with --list-cache.",
    )
    parser.add_argument(
        "--cache-limit",
        type=int,
        default=100,
        help="Max cached clips to show with --list-cache.",
    )
    parser.add_argument(
        "--max-split-preview",
        type=int,
        default=8,
        help="When not using --json, max split clip previews per event type.",
    )
    parser.add_argument(
        "--run-live-command",
        default=None,
        help="Execute a single natural-language command against GarageBand live automation.",
    )
    parser.add_argument(
        "--live-agent",
        action="store_true",
        help="Start interactive live GarageBand command loop.",
    )
    parser.add_argument(
        "--dry-run-live",
        action="store_true",
        help="Preview live automation actions without clicking keys/menu items.",
    )
    parser.add_argument(
        "--confirm-each-live",
        action="store_true",
        help="Prompt before each control action in live mode.",
    )
    parser.add_argument(
        "--garageband-app-name",
        default="GarageBand",
        help="macOS app/process name to automate (default: GarageBand).",
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
    if args.list_cache:
        clips = list_cached_clips(
            cache_dir=args.cache_dir,
            event_type=args.cache_event_type,
            limit=max(0, args.cache_limit),
        )
        if args.json:
            print(cached_clips_to_json(clips))
        else:
            print(cached_clips_to_pretty_text(clips))
        return 0
    if args.split_file:
        event_types = tuple(
            token.strip() for token in args.split_event_types.split(",") if token.strip()
        )
        try:
            report = split_song_to_cache(
                file_path=args.split_file,
                cache_dir=args.cache_dir,
                event_types=event_types or None,
                max_events_per_type=max(1, args.split_max_per_type),
                min_confidence=min(max(0.0, args.split_min_confidence), 1.0),
                pre_roll_seconds=max(0.0, args.split_pre_roll),
                post_roll_seconds=max(0.05, args.split_post_roll),
            )
        except Exception as exc:
            print(f"Song split failed: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(splitter_report_to_json(report))
        else:
            print(
                splitter_report_to_pretty_text(
                    report, max_preview_per_type=max(1, args.max_split_preview)
                )
            )
        return 0
    if args.analyze_file:
        try:
            report = analyze_song(args.analyze_file)
        except Exception as exc:
            print(f"Song analysis failed: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(analysis_to_json(report))
        else:
            print(
                analysis_to_pretty_text(
                    report, max_timestamps_per_type=max(1, args.max_analysis_preview)
                )
            )
        return 0
    if args.run_live_command:
        controller = AppleScriptController(app_name=args.garageband_app_name)
        agent = LiveGarageBandAgent(
            controller=controller,
            dry_run=args.dry_run_live,
            auto_activate=True,
        )
        report = agent.execute_prompt(
            args.run_live_command, confirm_each=args.confirm_each_live
        )
        if args.json:
            print(
                json.dumps(
                    {
                        "prompt": report.prompt,
                        "summary": report.summary,
                        "actions": [asdict(action) for action in report.actions],
                        "warnings": list(report.warnings),
                    },
                    indent=2,
                )
            )
        else:
            print(live_report_to_pretty_text(report))
        return 0
    if args.live_agent:
        controller = AppleScriptController(app_name=args.garageband_app_name)
        agent = LiveGarageBandAgent(
            controller=controller,
            dry_run=args.dry_run_live,
            auto_activate=True,
        )
        return run_live_agent_loop(agent, confirm_each=args.confirm_each_live)

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
