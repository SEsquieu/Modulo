import unittest
from pathlib import Path
import sys
import socket

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.common.contracts import JobStatus, RouteScope, WorkerRuntimeState
from modulo.client.hosting_readiness import HostingRuntimeProbeStatus
from modulo.client.app import HostingPrewarmResult
from modulo.client.ollama_loaded_models import LoadedOllamaModel, OllamaLoadedModelsStatus
from modulo.client.openclaw_discovery import OpenClawDiscoveryStatus
from modulo.worker.errors import WorkerExecutionError
from modulo.worker.executors import OllamaExecutor, StubExecutor
from modulo.prototype import LocalPrototypeHarness
from modulo.client.ollama_discovery import OllamaDiscoveryStatus


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


class ReadyRuntimeProbe:
    def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
        return HostingRuntimeProbeStatus(
            reachable=True,
            model_ready=True,
            summary=f"Ollama runtime resolved {model_id} successfully.",
            detail="ready runtime probe",
        )


class InstalledQwenDiscovery:
    def discover(self) -> OllamaDiscoveryStatus:
        return OllamaDiscoveryStatus(
            available=True,
            installed_model_ids=("qwen3.5:4b",),
            summary="Ollama is available with 1 local model.",
            details="installed qwen discovery",
        )


class InstalledLlamaDiscovery:
    def discover(self) -> OllamaDiscoveryStatus:
        return OllamaDiscoveryStatus(
            available=True,
            installed_model_ids=("llama3.1:8b",),
            summary="Ollama is available with 1 local llama model.",
            details="installed llama discovery",
        )


class FakeLoadedModelsDiscovery:
    def discover(self) -> OllamaLoadedModelsStatus:
        return OllamaLoadedModelsStatus(
            available=True,
            loaded_models=(
                LoadedOllamaModel(
                    model_id="llama3.1:8b",
                    display_name="llama3.1:8b",
                    expires_at="2099-01-01T00:00:00Z",
                    size_vram_bytes=4096,
                ),
            ),
            summary="1 Ollama model is currently loaded in memory.",
            details="fake loaded discovery",
        )


class MutableLoadedModelsDiscovery:
    def __init__(self) -> None:
        self.loaded_models: tuple[LoadedOllamaModel, ...] = ()

    def discover(self) -> OllamaLoadedModelsStatus:
        return OllamaLoadedModelsStatus(
            available=True,
            loaded_models=self.loaded_models,
            summary=(
                "No Ollama models are currently loaded in memory."
                if not self.loaded_models
                else f"{len(self.loaded_models)} Ollama model(s) are currently loaded in memory."
            ),
            details="mutable loaded discovery",
        )


class SuccessfulPrewarmer:
    def __init__(self, loaded_discovery: MutableLoadedModelsDiscovery) -> None:
        self.loaded_discovery = loaded_discovery

    def prewarm(self, model_id: str) -> HostingPrewarmResult:
        self.loaded_discovery.loaded_models = (
            LoadedOllamaModel(
                model_id=model_id,
                display_name=model_id,
                expires_at="2099-01-01T00:00:00Z",
                size_vram_bytes=2048,
            ),
        )
        return HostingPrewarmResult(
            ok=True,
            summary=f"Prewarm requested for {model_id}.",
            detail="fake prototype prewarm success",
        )


class FailedPrewarmer:
    def prewarm(self, model_id: str) -> HostingPrewarmResult:
        return HostingPrewarmResult(
            ok=False,
            summary=f"Prewarm failed for {model_id}.",
            detail="fake prototype prewarm failure",
        )


class BlockedRuntimeProbe:
    def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
        return HostingRuntimeProbeStatus(
            reachable=False,
            model_ready=False,
            summary=f"Ollama runtime could not resolve {model_id}.",
            detail="blocked runtime probe",
            error="blocked runtime probe",
        )


class FakeOllamaHTTPClient:
    def chat(self, base_url: str, payload: dict) -> dict:
        del base_url, payload
        return {"message": {"role": "assistant", "content": "hello from real ollama"}}


class FailingOllamaHTTPClient:
    def chat(self, base_url: str, payload: dict) -> dict:
        del base_url, payload
        raise WorkerExecutionError("real ollama request failed")


class TimeoutOllamaHTTPClient:
    def chat(self, base_url: str, payload: dict) -> dict:
        del base_url, payload
        raise WorkerExecutionError("Ollama request timed out")


class LocalPrototypeHarnessTests(unittest.TestCase):
    def test_selects_real_executor_when_runtime_probe_is_ready(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=ReadyRuntimeProbe(),
            ollama_http_client=FakeOllamaHTTPClient(),
        )

        self.assertIsInstance(harness.client.worker_bridge.executor, OllamaExecutor)
        self.assertEqual("real", harness.selected_executor_mode)
        self.assertIn("resolved", harness.selected_executor_summary)

    def test_default_real_executor_uses_extended_timeout_budget(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=ReadyRuntimeProbe(),
        )

        self.assertIsInstance(harness.client.worker_bridge.executor, OllamaExecutor)
        self.assertEqual(
            120.0,
            harness.client.worker_bridge.executor.http_client.timeout_seconds,
        )

    def test_falls_back_to_stub_executor_when_runtime_probe_is_blocked(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=BlockedRuntimeProbe(),
        )

        self.assertIsInstance(harness.client.worker_bridge.executor, StubExecutor)
        self.assertEqual("prototype", harness.selected_executor_mode)
        self.assertIn("could not resolve", harness.selected_executor_summary)

    def test_explicit_executor_override_is_preserved(self) -> None:
        executor = FailingExecutor()
        harness = LocalPrototypeHarness(
            executor=executor,
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=ReadyRuntimeProbe(),
        )

        self.assertIs(harness.client.worker_bridge.executor, executor)
        self.assertEqual("explicit", harness.selected_executor_mode)

    def test_boot_starts_hosting_and_registers_worker(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

        status = harness.boot()

        self.assertFalse(status.openclaw_configured)
        self.assertTrue(status.hosting_enabled)
        self.assertIsNotNone(status.worker)
        self.assertTrue(status.worker.registered_with_cloud)
        self.assertEqual(WorkerRuntimeState.IDLE, status.worker.runtime_state)

    def test_round_trip_completes_job_and_returns_response(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

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

    def test_real_round_trip_completes_through_supervised_path(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=ReadyRuntimeProbe(),
            ollama_http_client=FakeOllamaHTTPClient(),
        )

        result = harness.run_round_trip("real prototype hello")

        self.assertEqual("real", result.execution_mode)
        self.assertIn("resolved", result.execution_summary)
        self.assertEqual("hello from real ollama", result.response_text)
        self.assertIsNotNone(result.client_status.worker)
        self.assertEqual(JobStatus.COMPLETED, result.client_status.worker.last_job_status)

        completed_job = harness.service.get_job(result.job_id)
        self.assertIsNotNone(completed_job)
        self.assertEqual(JobStatus.COMPLETED, completed_job.status)
        self.assertEqual("real prototype hello", completed_job.request.messages[0].content)

    def test_single_machine_http_ingress_records_private_route_trace(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

        result = harness.run_round_trip("trace proof")

        self.assertTrue(result.trace_id)
        trace = harness.service.get_trace(result.trace_id)
        self.assertIsNotNone(trace)
        self.assertEqual(RouteScope.PRIVATE, trace.resolved_scope)
        self.assertEqual("prototype-private", trace.private_network_id)
        self.assertEqual(result.job_id, trace.job_id)
        self.assertEqual("completed", trace.final_status)
        self.assertEqual(harness.worker_id, trace.selected_worker_id)

    def test_boot_prewarms_real_model_when_prewarm_succeeds(self) -> None:
        loaded_discovery = MutableLoadedModelsDiscovery()
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=loaded_discovery,
            hosting_runtime_probe=ReadyRuntimeProbe(),
            hosting_prewarmer=SuccessfulPrewarmer(loaded_discovery),
            ollama_http_client=FakeOllamaHTTPClient(),
        )

        status = harness.boot()

        self.assertEqual("WARM", status.hosting_setup.warm_state_badge)
        self.assertIn("prewarm requested", status.hosting_setup.warm_summary.lower())

    def test_boot_surfaces_warm_failed_when_prewarm_fails(self) -> None:
        loaded_discovery = MutableLoadedModelsDiscovery()
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=loaded_discovery,
            hosting_runtime_probe=ReadyRuntimeProbe(),
            hosting_prewarmer=FailedPrewarmer(),
            ollama_http_client=FakeOllamaHTTPClient(),
        )

        status = harness.boot()

        self.assertEqual("WARM_FAILED", status.hosting_setup.warm_state_badge)
        self.assertIn("prewarm failed", status.hosting_setup.warm_summary.lower())

    def test_round_trip_uses_selected_installed_local_host_model(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledQwenDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=ReadyRuntimeProbe(),
            ollama_http_client=FakeOllamaHTTPClient(),
        )

        harness.client.set_hosting_model("qwen3.5:4b")
        result = harness.run_round_trip("local qwen hello")

        self.assertEqual("qwen3.5:4b", result.model_id)
        self.assertEqual("real", result.execution_mode)
        completed_job = harness.service.get_job(result.job_id)
        self.assertIsNotNone(completed_job)
        self.assertEqual("qwen3.5:4b", completed_job.request.model_id)

    def test_initial_host_model_syncs_to_first_available_local_model(self) -> None:
        harness = LocalPrototypeHarness(
            model_id="llama3.1:8b",
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledQwenDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=BlockedRuntimeProbe(),
        )

        status = harness.client.get_status()

        self.assertEqual("qwen3.5:4b", harness.model_id)
        self.assertEqual(("qwen3.5:4b",), harness.client.worker_bridge.config.enabled_models)
        self.assertEqual("qwen3.5:4b", status.hosting_setup.selected_model_id)

    def test_client_smoke_test_reports_success_through_client_surface(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

        harness.boot()
        status = harness.client.run_smoke_test("prototype smoke")
        onboarding = harness.client.get_onboarding_status()

        self.assertIsNotNone(status.smoke_test)
        self.assertTrue(status.smoke_test.ok)
        self.assertEqual("prototype smoke", status.smoke_test.user_message)
        self.assertTrue(onboarding.smoke_test_ok)
        self.assertEqual("", onboarding.smoke_test_error)

    def test_session_bridge_fetches_platform_state_without_hosting(self) -> None:
        harness = LocalPrototypeHarness(
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

        status = harness.client.get_status()

        self.assertTrue(status.platform.connected)
        self.assertIn("local prototype control plane", status.platform.summary)
        self.assertIn("local-only", status.platform.account_summary)
        self.assertEqual((), status.platform.network_models)
        self.assertEqual((), status.platform.private_models)
        self.assertEqual((), status.platform.public_models)
        self.assertTrue(status.platform.cloud_models)
        self.assertIn("No private/shared models", status.platform.buyer_routing_summary)
        self.assertIn("platform-managed", status.platform.buyer_config_summary)
        self.assertIn("private/shared", status.platform.private_visibility_summary.lower())
        self.assertIn("public scope is not yet exposed", status.platform.public_visibility_summary.lower())
        self.assertFalse(status.latest_route_trace.available)

    def test_session_bridge_reflects_network_models_after_hosting_registers(self) -> None:
        harness = LocalPrototypeHarness(
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

        harness.boot()
        status = harness.client.get_status()

        self.assertTrue(status.platform.connected)
        self.assertEqual(1, len(status.platform.network_models))
        self.assertEqual(1, len(status.platform.private_models))
        self.assertEqual((), status.platform.public_models)
        self.assertEqual("network", status.platform.network_models[0].source)
        self.assertEqual("private", status.platform.private_models[0].source)
        self.assertIn("private/shared", status.platform.buyer_routing_summary.lower())

    def test_route_trace_provider_reflects_latest_local_trace_after_round_trip(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

        result = harness.run_round_trip("trace visibility local")
        status = harness.client.get_status()

        self.assertTrue(status.latest_route_trace.available)
        self.assertEqual(result.trace_id, status.latest_route_trace.trace_id)
        self.assertEqual("private", status.latest_route_trace.scope)
        self.assertEqual(harness.worker_id, status.latest_route_trace.selected_worker_id)
        self.assertEqual("completed", status.latest_route_trace.final_status)

    def test_session_bridge_can_read_remote_platform_visibility(self) -> None:
        host_harness = LocalPrototypeHarness(
            model_id="qwen3.5:4b",
            ollama_discovery=InstalledQwenDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )
        buyer_harness = LocalPrototypeHarness(
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

        try:
            host_harness.boot()
            buyer_harness.client.session_bridge.set_target_url(host_harness.modulo_url)

            status = buyer_harness.client.get_status()

            self.assertTrue(status.platform.connected)
            self.assertIn("shared control plane", status.platform.summary)
            self.assertEqual(1, len(status.platform.network_models))
            self.assertEqual(1, len(status.platform.private_models))
            self.assertEqual((), status.platform.public_models)
            self.assertEqual("qwen3.5:4b", status.platform.network_models[0].model_id)
            self.assertEqual("qwen3.5:4b", status.platform.private_models[0].model_id)
            self.assertIn("private/shared", status.platform.buyer_routing_summary.lower())
            self.assertIn("public scope is not yet exposed", status.platform.public_visibility_summary.lower())
        finally:
            buyer_harness.shutdown()
            host_harness.shutdown()

    def test_route_trace_provider_can_read_remote_latest_trace(self) -> None:
        host_harness = LocalPrototypeHarness(
            model_id="qwen3.5:4b",
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledQwenDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=BlockedRuntimeProbe(),
        )
        buyer_harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=BlockedRuntimeProbe(),
        )

        try:
            result = host_harness.run_round_trip("remote trace visibility", buyer_id="buyer-remote")
            buyer_harness.set_platform_target_url(host_harness.modulo_url)

            status = buyer_harness.client.get_status()

            self.assertTrue(status.latest_route_trace.available)
            self.assertEqual(result.trace_id, status.latest_route_trace.trace_id)
            self.assertEqual("private", status.latest_route_trace.scope)
            self.assertEqual(host_harness.worker_id, status.latest_route_trace.selected_worker_id)
            self.assertEqual("completed", status.latest_route_trace.final_status)
        finally:
            buyer_harness.shutdown()
            host_harness.shutdown()

    def test_client_smoke_test_reports_failure_when_executor_fails(self) -> None:
        harness = LocalPrototypeHarness(
            executor=FailingExecutor(),
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

        harness.boot()
        status = harness.client.run_smoke_test("prototype failure")
        onboarding = harness.client.get_onboarding_status()

        self.assertIsNotNone(status.smoke_test)
        self.assertFalse(status.smoke_test.ok)
        self.assertIn("did not complete successfully", status.smoke_test.error)
        self.assertFalse(onboarding.worker_healthy)
        self.assertFalse(onboarding.smoke_test_ok)

    def test_real_execution_failure_surfaces_through_smoke_test_and_onboarding(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=ReadyRuntimeProbe(),
            ollama_http_client=FailingOllamaHTTPClient(),
        )

        harness.boot()
        status = harness.client.run_smoke_test("real prototype failure")
        onboarding = harness.client.get_onboarding_status()

        self.assertIsNotNone(status.smoke_test)
        self.assertFalse(status.smoke_test.ok)
        self.assertEqual("real", status.smoke_test.execution_mode)
        self.assertIn("resolved", status.smoke_test.execution_summary)
        self.assertIn("did not complete successfully", status.smoke_test.error)
        self.assertFalse(onboarding.worker_healthy)
        self.assertFalse(onboarding.smoke_test_ok)

    def test_real_execution_timeout_surfaces_as_clean_smoke_test_failure(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
            hosting_runtime_probe=ReadyRuntimeProbe(),
            ollama_http_client=TimeoutOllamaHTTPClient(),
        )

        harness.boot()
        status = harness.client.run_smoke_test("real timeout")
        onboarding = harness.client.get_onboarding_status()

        self.assertIsNotNone(status.smoke_test)
        self.assertFalse(status.smoke_test.ok)
        self.assertEqual("real", status.smoke_test.execution_mode)
        self.assertIn("timed out", status.smoke_test.error.lower())
        self.assertFalse(onboarding.smoke_test_ok)

    def test_activity_visibility_tracks_recent_jobs_and_continuity(self) -> None:
        harness = LocalPrototypeHarness(
            openclaw_discovery=FakePrototypeOpenClawDiscovery(),
            ollama_discovery=InstalledLlamaDiscovery(),
            ollama_loaded_models_discovery=FakeLoadedModelsDiscovery(),
        )

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
