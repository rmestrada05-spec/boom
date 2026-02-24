"""Live GarageBand automation via macOS Accessibility and AppleScript.

This module turns natural-language requests into executable GarageBand control
actions. It uses:

- action plans from `planner.build_action_plan`
- control metadata from `knowledge_base`
- AppleScript (`osascript`) for keystrokes/menu clicks on macOS
"""

from __future__ import annotations

import platform
import shlex
import subprocess
import time
from dataclasses import dataclass, field

from .knowledge_base import get_control
from .planner import build_action_plan


@dataclass(frozen=True)
class ShortcutCombo:
    """A keyboard shortcut in key+modifier form."""

    key: str
    modifiers: tuple[str, ...] = ()
    key_code: int | None = None


@dataclass(frozen=True)
class LiveActionResult:
    """Result of attempting a single control action."""

    control_id: str
    step_title: str
    status: str
    detail: str


@dataclass(frozen=True)
class LiveRunReport:
    """Result of executing a prompt live against GarageBand."""

    prompt: str
    summary: str
    actions: tuple[LiveActionResult, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)


MODIFIER_ALIASES: dict[str, str] = {
    "cmd": "command",
    "command": "command",
    "⌘": "command",
    "option": "option",
    "opt": "option",
    "⌥": "option",
    "shift": "shift",
    "⇧": "shift",
    "control": "control",
    "ctrl": "control",
    "⌃": "control",
}

SPECIAL_KEY_CODES: dict[str, int] = {
    "space": 49,
    "tab": 48,
    "return": 36,
    "enter": 76,
    "delete": 51,
    "escape": 53,
    "esc": 53,
    "up": 126,
    "down": 125,
    "left": 123,
    "right": 124,
}


# Some controls are practical with menu navigation even if no shortcut exists.
CONTROL_MENU_PATHS: dict[str, tuple[str, ...]] = {
    "help_quick_help": ("Help", "Quick Help"),
    "share_export_song": ("Share", "Export Song to Disk..."),
    "master_track_show": ("Track", "Show Master Track"),
}


# Some controls are not reliably scriptable in a DAW-agnostic way and should
# be surfaced as explicit manual actions to keep automation safe.
MANUAL_REQUIRED_CONTROLS: dict[str, str] = {
    "lcd_tempo": "Set project tempo in the LCD tempo field.",
    "lcd_key_signature": "Set key signature from the LCD key field.",
    "lcd_time_signature": "Set time signature from the LCD meter field.",
    "track_volume": "Adjust track volume in track header or automation lane.",
    "track_pan": "Adjust track pan in track header.",
    "send_reverb": "Adjust track reverb send in Smart Controls.",
    "send_echo": "Adjust track echo send in Smart Controls.",
    "plugin_slot": "Open Smart Controls > Plug-ins to insert effects.",
    "step_sequencer_pattern": "Edit the region in Step Sequencer view.",
    "note_velocity": "Adjust MIDI note velocity in Piano Roll.",
    "plugin_channel_eq": "Open plug-in slot and load Channel EQ.",
    "plugin_compressor": "Open plug-in slot and load Compressor.",
    "plugin_distortion": "Open plug-in slot and load Distortion.",
    "plugin_overdrive": "Open plug-in slot and load Overdrive.",
    "plugin_noise_gate": "Open plug-in slot and load Noise Gate.",
    "plugin_chorus": "Open plug-in slot and load Chorus.",
    "plugin_limiter": "Open plug-in slot and load Limiter.",
}


class AppleScriptController:
    """Thin wrapper over osascript for GarageBand UI automation."""

    def __init__(
        self,
        app_name: str = "GarageBand",
        execution_pause_seconds: float = 0.12,
        command_timeout_seconds: float = 8.0,
    ) -> None:
        self.app_name = app_name
        self.execution_pause_seconds = max(0.0, execution_pause_seconds)
        self.command_timeout_seconds = max(1.0, command_timeout_seconds)

    def activate_app(self) -> None:
        script = f'tell application "{_escape_applescript(self.app_name)}" to activate'
        self.run_applescript(script)
        time.sleep(self.execution_pause_seconds)

    def press_shortcut(self, shortcut: ShortcutCombo) -> None:
        using_clause = ""
        if shortcut.modifiers:
            mods = ", ".join(f"{mod} down" for mod in shortcut.modifiers)
            using_clause = f" using {{{mods}}}"

        if shortcut.key_code is not None:
            key_line = f"key code {shortcut.key_code}{using_clause}"
        else:
            escaped_key = _escape_applescript(shortcut.key)
            key_line = f'keystroke "{escaped_key}"{using_clause}'

        script = "\n".join(
            [
                f'tell application "{_escape_applescript(self.app_name)}" to activate',
                'tell application "System Events"',
                f'  tell process "{_escape_applescript(self.app_name)}"',
                "    set frontmost to true",
                f"    {key_line}",
                "  end tell",
                "end tell",
            ]
        )
        self.run_applescript(script)
        time.sleep(self.execution_pause_seconds)

    def click_menu_path(self, path: tuple[str, ...]) -> None:
        if len(path) != 2:
            raise ValueError("Only top-level menu item paths are currently supported.")

        menu_name, item_name = path
        script = "\n".join(
            [
                f'tell application "{_escape_applescript(self.app_name)}" to activate',
                'tell application "System Events"',
                f'  tell process "{_escape_applescript(self.app_name)}"',
                "    set frontmost to true",
                (
                    f'    click menu item "{_escape_applescript(item_name)}" of menu 1 of '
                    f'menu bar item "{_escape_applescript(menu_name)}" of menu bar 1'
                ),
                "  end tell",
                "end tell",
            ]
        )
        self.run_applescript(script)
        time.sleep(self.execution_pause_seconds)

    def run_applescript(self, script: str) -> None:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=self.command_timeout_seconds,
        )


class LiveGarageBandAgent:
    """Executes GarageBand controls from natural-language action plans."""

    def __init__(
        self,
        controller: AppleScriptController,
        dry_run: bool = False,
        auto_activate: bool = True,
    ) -> None:
        self.controller = controller
        self.dry_run = dry_run
        self.auto_activate = auto_activate

    def ensure_environment(self) -> tuple[str, ...]:
        warnings: list[str] = []
        if platform.system() != "Darwin":
            warnings.append(
                "Live GarageBand automation requires macOS and was not executed."
            )
        return tuple(warnings)

    def execute_prompt(
        self,
        prompt: str,
        confirm_each: bool = False,
        auto_activate: bool | None = None,
    ) -> LiveRunReport:
        direct_controls = _direct_control_ids_from_prompt(prompt)
        run_direct_mode = _should_run_direct_mode(prompt, direct_controls)

        plan = None
        warnings: list[str] = []
        if not run_direct_mode:
            plan = build_action_plan(prompt)
            warnings.extend(plan.warnings)
        warnings.extend(self.ensure_environment())
        actions: list[LiveActionResult] = []

        should_activate = self.auto_activate if auto_activate is None else auto_activate
        if should_activate and not self.dry_run and platform.system() == "Darwin":
            try:
                self.controller.activate_app()
            except Exception as exc:  # pragma: no cover - platform-dependent
                warnings.append(
                    "Could not activate GarageBand automatically. "
                    f"Bring it to foreground manually. ({exc})"
                )

        if run_direct_mode:
            step_bundle = [("Direct command mapping", tuple(direct_controls), {})]
            summary = "GarageBand live direct-control execution."
        else:
            assert plan is not None
            step_bundle = [
                (step.title, step.control_ids, step.parameters) for step in plan.steps
            ]
            summary = plan.summary

        for step_title, control_ids, parameters in step_bundle:
            for control_id in control_ids:
                if confirm_each and not _confirm_step(step_title, control_id):
                    actions.append(
                        LiveActionResult(
                            control_id=control_id,
                            step_title=step_title,
                            status="skipped_by_user",
                            detail="User skipped this control.",
                        )
                    )
                    continue
                actions.append(
                    self.execute_control(
                        control_id=control_id,
                        step_title=step_title,
                        parameters=parameters,
                    )
                )

        return LiveRunReport(
            prompt=prompt,
            summary=summary,
            actions=tuple(actions),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def execute_control(
        self,
        control_id: str,
        step_title: str = "",
        parameters: dict[str, str] | None = None,
    ) -> LiveActionResult:
        control = get_control(control_id)
        if control is None:
            return LiveActionResult(
                control_id=control_id,
                step_title=step_title,
                status="unknown_control",
                detail="Control ID is not in knowledge base.",
            )

        manual_instruction = MANUAL_REQUIRED_CONTROLS.get(control_id)
        if manual_instruction:
            details = manual_instruction
            if control_id == "lcd_tempo" and parameters and parameters.get("tempo_bpm"):
                details = f"{manual_instruction} Target tempo: {parameters['tempo_bpm']} BPM."
            return LiveActionResult(
                control_id=control_id,
                step_title=step_title,
                status="manual_required",
                detail=details,
            )

        menu_path = CONTROL_MENU_PATHS.get(control_id)
        shortcut = parse_shortcut(control.shortcut)

        if self.dry_run:
            if shortcut:
                description = f'Dry run: would press shortcut "{control.shortcut}".'
                return LiveActionResult(control_id, step_title, "dry_run", description)
            if menu_path:
                description = (
                    "Dry run: would click menu path "
                    + " > ".join(shlex.quote(item) for item in menu_path)
                    + "."
                )
                return LiveActionResult(control_id, step_title, "dry_run", description)
            return LiveActionResult(
                control_id,
                step_title,
                "unsupported",
                "No shortcut or menu mapping available for automation.",
            )

        if platform.system() != "Darwin":
            return LiveActionResult(
                control_id=control_id,
                step_title=step_title,
                status="unsupported_platform",
                detail="Live automation only runs on macOS.",
            )

        try:
            if shortcut:
                self.controller.press_shortcut(shortcut)
                return LiveActionResult(
                    control_id=control_id,
                    step_title=step_title,
                    status="executed",
                    detail=f'Pressed shortcut "{control.shortcut}".',
                )
            if menu_path:
                self.controller.click_menu_path(menu_path)
                return LiveActionResult(
                    control_id=control_id,
                    step_title=step_title,
                    status="executed",
                    detail="Clicked menu path: " + " > ".join(menu_path),
                )
            return LiveActionResult(
                control_id=control_id,
                step_title=step_title,
                status="unsupported",
                detail="No shortcut or menu mapping available for automation.",
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - platform-dependent
            stderr = (exc.stderr or "").strip()
            message = stderr or str(exc)
            return LiveActionResult(
                control_id=control_id,
                step_title=step_title,
                status="automation_error",
                detail=(
                    "AppleScript call failed. Ensure Accessibility + Automation "
                    f"permissions are enabled. ({message})"
                ),
            )
        except Exception as exc:  # pragma: no cover - platform-dependent
            return LiveActionResult(
                control_id=control_id,
                step_title=step_title,
                status="automation_error",
                detail=str(exc),
            )


def parse_shortcut(shortcut: str) -> ShortcutCombo | None:
    """Parse shortcut strings like 'Option-Command-N' into executable parts."""
    if not shortcut or not shortcut.strip():
        return None

    parts = [part.strip() for part in shortcut.replace("+", "-").split("-") if part.strip()]
    if not parts:
        return None

    modifiers: list[str] = []
    key_part: str | None = None
    for part in parts:
        lowered = part.lower()
        if lowered in MODIFIER_ALIASES:
            modifiers.append(MODIFIER_ALIASES[lowered])
            continue
        key_part = part

    if key_part is None:
        key_part = parts[-1]

    key_normalized = key_part.strip().lower()
    if key_normalized in SPECIAL_KEY_CODES:
        return ShortcutCombo(
            key=key_normalized,
            modifiers=tuple(dict.fromkeys(modifiers)),
            key_code=SPECIAL_KEY_CODES[key_normalized],
        )

    if len(key_part) == 1:
        key = key_part.lower()
    else:
        key = key_part
    return ShortcutCombo(key=key, modifiers=tuple(dict.fromkeys(modifiers)))


def live_report_to_pretty_text(report: LiveRunReport) -> str:
    """Render live execution report to a readable summary."""
    lines = [f"Live plan: {report.summary}", f"Prompt: {report.prompt}", "Actions:"]
    for index, action in enumerate(report.actions, start=1):
        step_hint = f" [{action.step_title}]" if action.step_title else ""
        lines.append(
            f"{index}. {action.control_id}{step_hint} -> {action.status}: {action.detail}"
        )
    if report.warnings:
        lines.append("Warnings:")
        for warning in report.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def run_live_agent_loop(
    agent: LiveGarageBandAgent,
    confirm_each: bool = False,
) -> int:
    """Interactive terminal loop for live GarageBand command execution."""
    print(
        "GarageBand Live Agent ready.\n"
        "Type a prompt to run it, or use:\n"
        "  /help      show commands\n"
        "  /quit      exit\n"
        "  /plan ...  print plan without executing controls\n"
        "  /control <control_id>  run a single control\n"
    )
    while True:
        try:
            raw = input("gb-live> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not raw:
            continue
        lowered = raw.lower()
        if lowered in {"/quit", "quit", "exit"}:
            return 0
        if lowered in {"/help", "help"}:
            print(
                "Commands:\n"
                "  /help                        Show this message\n"
                "  /quit                        Exit live mode\n"
                "  /plan <prompt>               Build and print a plan only\n"
                "  /control <control_id>        Run one control directly\n"
                "  <free text>                  Build plan and execute controls"
            )
            continue
        if lowered.startswith("/plan "):
            plan_prompt = raw[6:].strip()
            if not plan_prompt:
                print("Provide text after /plan.")
                continue
            preview_agent = LiveGarageBandAgent(
                controller=agent.controller,
                dry_run=True,
                auto_activate=False,
            )
            report = preview_agent.execute_prompt(
                plan_prompt,
                confirm_each=False,
                auto_activate=False,
            )
            print(live_report_to_pretty_text(report))
            continue
        if lowered.startswith("/control "):
            control_id = raw[9:].strip()
            if not control_id:
                print("Provide a control_id after /control.")
                continue
            result = agent.execute_control(control_id=control_id, step_title="direct")
            report = LiveRunReport(
                prompt=f"/control {control_id}",
                summary="Direct control execution",
                actions=(result,),
                warnings=agent.ensure_environment(),
            )
            print(live_report_to_pretty_text(report))
            continue

        report = agent.execute_prompt(raw, confirm_each=confirm_each)
        print(live_report_to_pretty_text(report))


def _confirm_step(step_title: str, control_id: str) -> bool:
    prompt = f"Execute control '{control_id}' in step '{step_title}'? [Y/n]: "
    response = input(prompt).strip().lower()
    if response in {"", "y", "yes"}:
        return True
    return False


def _escape_applescript(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _direct_control_ids_from_prompt(prompt: str) -> list[str]:
    lowered = prompt.lower()
    controls: list[str] = []
    keyword_map: tuple[tuple[str, str], ...] = (
        ("play", "transport_play"),
        ("stop", "transport_stop"),
        ("pause", "transport_stop"),
        ("record", "transport_record"),
        ("loop", "transport_cycle"),
        ("cycle", "transport_cycle"),
        ("metronome", "transport_metronome"),
        ("click", "transport_metronome"),
        ("new track", "track_new"),
        ("add track", "track_new"),
        ("library", "library_toggle"),
        ("smart controls", "smart_controls_toggle"),
        ("editor", "editor_toggle"),
        ("automation", "automation_show"),
        ("export", "share_export_song"),
        ("bounce", "share_export_song"),
    )
    for keyword, control_id in keyword_map:
        if keyword in lowered:
            controls.append(control_id)

    # Preserve order while deduplicating.
    seen: set[str] = set()
    deduped: list[str] = []
    for control_id in controls:
        if control_id in seen:
            continue
        deduped.append(control_id)
        seen.add(control_id)
    return deduped


def _should_run_direct_mode(prompt: str, direct_controls: list[str]) -> bool:
    if not direct_controls:
        return False
    lowered = prompt.lower()
    production_keywords = (
        "bpm",
        "bass",
        "synth",
        "guitar",
        "vocal",
        "eq",
        "compress",
        "reverb",
        "delay",
        "mix",
        "gabber",
        "master",
    )
    if any(keyword in lowered for keyword in production_keywords):
        return False
    return True
