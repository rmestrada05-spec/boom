"""GarageBand director package.

Maps natural language production requests to GarageBand control-level steps.
"""

from .knowledge_base import GARAGEBAND_CONTROLS, get_control, search_controls
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
    "build_action_plan",
    "cached_clips_to_json",
    "cached_clips_to_pretty_text",
    "get_control",
    "list_cached_clips",
    "parse_intent",
    "plan_to_json",
    "plan_to_pretty_text",
    "search_controls",
    "split_song_to_cache",
    "splitter_report_to_json",
    "splitter_report_to_pretty_text",
]
