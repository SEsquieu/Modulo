import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.common.contracts import JobStatus, WorkerRuntimeState
from modulo.client.openclaw_discovery import OpenClawDiscoveryStatus
from modulo.worker.errors import WorkerExecutionError
from modulo.prototype import LocalPrototypeHarness


class FailingExecutor:
    def execute(self, worker_id: str, request) -> str:
        del worker_id, request
        raise WorkerExecutionError("prototype executor failed")


class FakePrototypeOpenClawDiscovery:
    def discover(self) -> OpenClawDiscoveryStatus:
        return OpenClawDiscoveryStatus(
            installed=False,
            config_present=False,
            configured_for_modulo=False,
            state="not_installed",
            summary="OpenClaw was not detected on this machine.",
            details="No OpenClaw install or config footprint was found.",
        )


class LocalPrototypeHarnessTests(unittest.TestCase):
    def test_boot_starts_hosting_and_registers_worker(self) -> None:
        harness = LocalPrototypeHarness(openclaw_discovery=FakePrototypeOpenClawDiscovery())

        status = harness.boot()

        self.assertFalse(status.openclaw_configured)
        self.assertTrue(status.hosting_enabled)
        self.assertIsNotNone(status.worker)
        self.assertTrue(status.worker.registered_with_cloud)
        self.assertEqual(WorkerRuntimeState.IDLE, status.worker.runtime_state)

    def test_round_trip_completes_job_and_returns_response(self) -> None:
        harness = LocalPrototypeHarness(openclaw_discovery=FakePrototypeOpenClawDiscovery())

        result = harness.run_round_trip("prototype hello")

        self.assertEqual("llama3.1:8b", result.model_id)
        self.assertEqual("prototype hello", result.user_message)
        self.assertIn("prototype worker", result.response_text)
        self.assertIsNotNone(result.client_status.worker)
        self.assertEqual(JobStatus.COMPLETED, result.client_status.worker.last_job_status)

        completed_job = harness.service.get_job(result.job_id)
        self.assertIsNotNone(completed_job)
        self.assertEqual(JobStatus.COMPLETED, completed_job.status)
        self.assertEqual("prototype hello", completed_job.request.messages[0].content)

    def test_client_smoke_test_reports_success_through_client_surface(self) -> None:
        harness = LocalPrototypeHarness(openclaw_discovery=FakePrototypeOpenClawDiscovery())

        harness.boot()
        status = harness.client.run_smoke_test("prototype smoke")
        onboarding = harness.client.get_onboarding_status()

        self.assertIsNotNone(status.smoke_test)
        self.assertTrue(status.smoke_test.ok)
        self.assertEqual("prototype smoke", status.smoke_test.user_message)
        self.assertTrue(onboarding.smoke_test_ok)
        self.assertEqual("", onboarding.smoke_test_error)

    def test_session_bridge_fetches_platform_state_without_hosting(self) -> None:
        harness = LocalPrototypeHarness()

        status = harness.client.get_status()

        self.assertTrue(status.platform.connected)
        self.assertIn("local prototype control plane", status.platform.summary)
        self.assertIn("local-only", status.platform.account_summary)
        self.assertEqual((), status.platform.network_models)
        self.assertTrue(status.platform.cloud_models)
        self.assertIn("No network models", status.platform.buyer_routing_summary)
        self.assertIn("platform-managed", status.platform.buyer_config_summary)

    def test_session_bridge_reflects_network_models_after_hosting_registers(self) -> None:
        harness = LocalPrototypeHarness()

        harness.boot()
        status = harness.client.get_status()

        self.assertTrue(status.platform.connected)
        self.assertEqual(1, len(status.platform.network_models))
        self.assertEqual("network", status.platform.network_models[0].source)
        self.assertIn("currently advertised", status.platform.buyer_routing_summary)

    def test_client_smoke_test_reports_failure_when_executor_fails(self) -> None:
        harness = LocalPrototypeHarness(
            executor=FailingExecutor(),
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
        )

        harness.boot()
        status = harness.client.run_smoke_test("prototype failure")
        onboarding = harness.client.get_onboarding_status()

        self.assertIsNotNone(status.smoke_test)
        self.assertFalse(status.smoke_test.ok)
        self.assertIn("did not complete successfully", status.smoke_test.error)
        self.assertFalse(onboarding.worker_healthy)
        self.assertFalse(onboarding.smoke_test_ok)

    def test_activity_visibility_tracks_recent_jobs_and_continuity(self) -> None:
        harness = LocalPrototypeHarness(openclaw_discovery=FakePrototypeOpenClawDiscovery())

        harness.run_round_trip("first buyer turn", buyer_id="buyer-a")
        harness.run_round_trip("second buyer turn", buyer_id="buyer-a")
        activity = harness.get_activity_visibility()

        self.assertIn("Buyer continuity reused", activity.continuity_summary)
        self.assertGreaterEqual(len(activity.recent_activity), 2)
        self.assertEqual("buyer-a", activity.recent_activity[0].buyer_id)
        self.assertIn(
            activity.recent_activity[0].continuity_hint,
            {"Continuity lease reused", "Fresh routing decision"},
        )


if __name__ == "__main__":
    unittest.main()
