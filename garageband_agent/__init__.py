"""GarageBand director package.

Maps natural language production requests to GarageBand control-level steps.
"""

from .knowledge_base import GARAGEBAND_CONTROLS, get_control, search_controls
from .planner import build_action_plan, parse_intent, plan_to_json, plan_to_pretty_text

__all__ = [
    "GARAGEBAND_CONTROLS",
    "build_action_plan",
    "get_control",
    "parse_intent",
    "plan_to_json",
    "plan_to_pretty_text",
    "search_controls",
]
