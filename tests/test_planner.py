import json
import unittest

from garageband_agent.planner import build_action_plan, parse_intent, plan_to_json


class PlannerTests(unittest.TestCase):
    def test_parses_gabber_bass_prompt(self) -> None:
        intent = parse_intent("add a bass sound at 160bpm to have a gabber feel")
        self.assertEqual(intent.tempo_bpm, 160)
        self.assertIn("gabber", intent.genres)
        self.assertIn("bass", intent.instruments)

    def test_builds_gabber_plan_with_distortion(self) -> None:
        plan = build_action_plan("add a bass sound at 160bpm to have a gabber feel")
        titles = [step.title for step in plan.steps]
        self.assertIn("Set project tempo", titles)
        self.assertTrue(any("hardcore saturation" in title.lower() for title in titles))

    def test_extracts_playback_targets(self) -> None:
        prompt = (
            "Tune for my 2011 Jetta TDI, a club that is 80x45x16 ft, "
            "and headphones Sony WH-1000XM5."
        )
        intent = parse_intent(prompt)
        types = [target.target_type for target in intent.playback_targets]
        self.assertIn("car", types)
        self.assertIn("club", types)
        self.assertIn("headphones", types)
        club_target = next(t for t in intent.playback_targets if t.target_type == "club")
        self.assertEqual(club_target.details.get("dimensions"), "80x45x16")

    def test_plan_json_is_valid(self) -> None:
        plan = build_action_plan("make this brighter and cleaner")
        rendered = plan_to_json(plan)
        decoded = json.loads(rendered)
        self.assertIn("steps", decoded)
        self.assertGreater(len(decoded["steps"]), 0)


if __name__ == "__main__":
    unittest.main()
