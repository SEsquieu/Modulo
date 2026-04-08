import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.gui.controller import GuiAppController


class GuiAppControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = GuiAppController.build_default()

    def test_refresh_reports_initial_shell_state(self) -> None:
        state = self.controller.refresh()

        self.assertTrue(state.connected_to_modulo)
        self.assertFalse(state.openclaw_connected)
        self.assertFalse(state.hosting_enabled)
        self.assertEqual("stopped", state.worker_runtime_state)
        self.assertEqual("No smoke test run yet.", state.smoke_test_summary)

    def test_start_hosting_and_smoke_test_update_state(self) -> None:
        self.controller.connect_openclaw()
        started = self.controller.start_hosting()
        smoked = self.controller.run_smoke_test("gui smoke")

        self.assertTrue(started.hosting_enabled)
        self.assertTrue(started.worker_registered)
        self.assertTrue(started.worker_healthy)
        self.assertTrue(smoked.smoke_test_ok)
        self.assertIn("Smoke test passed", smoked.smoke_test_summary)
        self.assertIn("gui smoke", smoked.smoke_test_details)


if __name__ == "__main__":
    unittest.main()
