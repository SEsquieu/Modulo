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
        self.assertTrue(state.connect_action_enabled)
        self.assertTrue(state.start_action_enabled)
        self.assertFalse(state.stop_action_enabled)
        self.assertFalse(state.smoke_action_enabled)
        self.assertIn("Connect OpenClaw", state.home_subtitle)
        self.assertIn("not connected", state.connection_summary.lower())
        self.assertIn("Not registered", state.worker_registration_text)
        self.assertIn("idle", state.worker_health_summary.lower())
        self.assertIn("not processed a job", state.worker_activity_summary)
        self.assertEqual("GUI smoke test request", state.smoke_test_prompt)
        self.assertEqual("Not run yet", state.smoke_test_result_label)
        self.assertIn("Run a smoke test", state.diagnostics_summary)
        self.assertIn("Last worker error: None", state.diagnostics_details)
        self.assertEqual("Enable Hosting", state.secondary_action_label)
        self.assertEqual("stopped", state.worker_runtime_state)
        self.assertEqual("No smoke test run yet.", state.smoke_test_summary)

    def test_start_hosting_and_smoke_test_update_state(self) -> None:
        self.controller.connect_openclaw()
        started = self.controller.start_hosting()
        smoked = self.controller.run_smoke_test("gui smoke")

        self.assertTrue(started.hosting_enabled)
        self.assertTrue(started.worker_registered)
        self.assertTrue(started.worker_healthy)
        self.assertFalse(started.start_action_enabled)
        self.assertTrue(started.stop_action_enabled)
        self.assertTrue(started.restart_action_enabled)
        self.assertTrue(started.smoke_action_enabled)
        self.assertIn("Hosting is enabled", started.hosting_summary)
        self.assertTrue(smoked.smoke_test_ok)
        self.assertEqual("PASS", smoked.smoke_status_badge)
        self.assertIn("Smoke test passed", smoked.smoke_test_summary)
        self.assertIn("gui smoke", smoked.smoke_test_details)
        self.assertEqual("gui smoke", smoked.smoke_test_prompt)
        self.assertEqual("Pass", smoked.smoke_test_result_label)
        self.assertIn("diagnostics look healthy", smoked.diagnostics_summary)
        self.assertIn("Response:", smoked.diagnostics_details)
        self.assertTrue(smoked.last_job_id)
        self.assertEqual("completed", smoked.last_job_status)
        self.assertIn("finished with status completed", smoked.worker_activity_summary)


if __name__ == "__main__":
    unittest.main()
