"""GarageBand director package.

Maps natural language production requests to GarageBand control-level steps.
"""

from .knowledge_base import GARAGEBAND_CONTROLS, get_control, search_controls
from .live_agent import (
    AppleScriptController,
    LiveActionResult,
    LiveGarageBandAgent,
    LiveRunReport,
    ShortcutCombo,
    live_report_to_pretty_text,
    parse_shortcut,
    run_live_agent_loop,
)
from .planner import build_action_plan, parse_intent, plan_to_json, plan_to_pretty_text
from .song_analyzer import (
    SongAnalysisReport,
    TimestampEvent,
    analysis_to_json,
    analysis_to_pretty_text,
    analyze_song,
)
from .splitter import (
    CachedClip,
    SplitterReport,
    cached_clips_to_json,
    cached_clips_to_pretty_text,
    list_cached_clips,
    split_song_to_cache,
    splitter_report_to_json,
    splitter_report_to_pretty_text,
)

__all__ = [
    "GARAGEBAND_CONTROLS",
    "CachedClip",
    "SongAnalysisReport",
    "SplitterReport",
    "TimestampEvent",
    "analysis_to_json",
    "analysis_to_pretty_text",
    "analyze_song",
    "AppleScriptController",
    "build_action_plan",
    "cached_clips_to_json",
    "cached_clips_to_pretty_text",
    "get_control",
    "LiveActionResult",
    "LiveGarageBandAgent",
    "LiveRunReport",
    "live_report_to_pretty_text",
    "list_cached_clips",
    "parse_intent",
    "parse_shortcut",
    "plan_to_json",
    "plan_to_pretty_text",
    "run_live_agent_loop",
    "search_controls",
    "ShortcutCombo",
    "split_song_to_cache",
    "splitter_report_to_json",
    "splitter_report_to_pretty_text",
]
