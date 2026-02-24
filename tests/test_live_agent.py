import unittest

from garageband_agent.live_agent import (
    LiveGarageBandAgent,
    live_report_to_pretty_text,
    parse_shortcut,
)


class _FakeController:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def activate_app(self) -> None:
        self.calls.append(("activate_app", None))

    def press_shortcut(self, shortcut: object) -> None:
        self.calls.append(("press_shortcut", shortcut))

    def click_menu_path(self, path: object) -> None:
        self.calls.append(("click_menu_path", path))


class LiveAgentTests(unittest.TestCase):
    def test_parse_shortcut_option_command(self) -> None:
        shortcut = parse_shortcut("Option-Command-N")
        self.assertIsNotNone(shortcut)
        assert shortcut is not None
        self.assertEqual(shortcut.key, "n")
        self.assertEqual(set(shortcut.modifiers), {"option", "command"})
        self.assertIsNone(shortcut.key_code)

    def test_parse_shortcut_special_key(self) -> None:
        shortcut = parse_shortcut("Space")
        self.assertIsNotNone(shortcut)
        assert shortcut is not None
        self.assertEqual(shortcut.key_code, 49)

    def test_manual_required_control(self) -> None:
        agent = LiveGarageBandAgent(controller=_FakeController(), dry_run=True)
        result = agent.execute_control(
            control_id="lcd_tempo",
            step_title="tempo setup",
            parameters={"tempo_bpm": "160"},
        )
        self.assertEqual(result.status, "manual_required")
        self.assertIn("160", result.detail)

    def test_dry_run_execution(self) -> None:
        controller = _FakeController()
        agent = LiveGarageBandAgent(controller=controller, dry_run=True)
        result = agent.execute_control(
            control_id="transport_play",
            step_title="playback",
        )
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(len(controller.calls), 0)

    def test_execute_prompt_returns_actions(self) -> None:
        agent = LiveGarageBandAgent(controller=_FakeController(), dry_run=True)
        report = agent.execute_prompt("add a bass sound at 160bpm to have a gabber feel")
        self.assertGreater(len(report.actions), 0)
        statuses = {action.status for action in report.actions}
        self.assertTrue("dry_run" in statuses or "manual_required" in statuses)
        rendered = live_report_to_pretty_text(report)
        self.assertIn("Live plan:", rendered)

    def test_direct_mode_transport_prompt(self) -> None:
        agent = LiveGarageBandAgent(controller=_FakeController(), dry_run=True)
        report = agent.execute_prompt("play and loop")
        control_ids = [action.control_id for action in report.actions]
        self.assertIn("transport_play", control_ids)
        self.assertIn("transport_cycle", control_ids)
        self.assertNotIn("track_new", control_ids)


if __name__ == "__main__":
    unittest.main()
