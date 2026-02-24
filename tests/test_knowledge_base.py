import unittest

from garageband_agent.knowledge_base import GARAGEBAND_CONTROLS, get_control, search_controls


class KnowledgeBaseTests(unittest.TestCase):
    def test_controls_are_loaded(self) -> None:
        self.assertGreater(len(GARAGEBAND_CONTROLS), 20)

    def test_lookup_by_id(self) -> None:
        control = get_control("transport_metronome")
        self.assertIsNotNone(control)
        assert control is not None
        self.assertIn("Metronome", control.label)

    def test_search_finds_eq(self) -> None:
        controls = search_controls("eq")
        ids = [control.control_id for control in controls]
        self.assertIn("plugin_channel_eq", ids)

    def test_search_with_empty_query_returns_defaults(self) -> None:
        controls = search_controls("")
        self.assertGreater(len(controls), 0)


if __name__ == "__main__":
    unittest.main()
