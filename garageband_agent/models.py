"""Shared data models for the GarageBand director agent."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GarageBandControl:
    """A discoverable GarageBand control/button/menu item."""

    control_id: str
    label: str
    location: str
    purpose: str
    shortcut: str = ""
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlaybackTarget:
    """A listening context the user wants the mix to translate to."""

    target_type: str
    description: str
    details: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductionIntent:
    """Natural language parsed into production-friendly attributes."""

    raw_prompt: str
    tempo_bpm: int | None = None
    genres: tuple[str, ...] = ()
    instruments: tuple[str, ...] = ()
    descriptors: tuple[str, ...] = ()
    playback_targets: tuple[PlaybackTarget, ...] = ()


@dataclass(frozen=True)
class ActionStep:
    """An executable GarageBand action with rationale."""

    title: str
    instructions: str
    why: str
    control_ids: tuple[str, ...] = ()
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionPlan:
    """Ordered steps generated from parsed intent."""

    summary: str
    intent: ProductionIntent
    steps: tuple[ActionStep, ...]
    warnings: tuple[str, ...] = ()
