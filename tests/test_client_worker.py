import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.client.app import ModuloClientSupervisor, PlatformModelListing, PlatformSessionStatus
from modulo.client.hosting_readiness import HostingRuntimeProbeStatus
from modulo.client.openclaw_discovery import OpenClawDiscoveryStatus
from modulo.client.ollama_discovery import OllamaDiscoveryStatus
from modulo.cloud.http import ModuloHTTPApp
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService
from modulo.common.contracts import (
    ChatMessage,
    ChatRequest,
    ExecutionMode,
    JobStatus,
    WorkerBridgeConfig,
    WorkerRuntimeState,
)
from modulo.worker.runtime import InMemoryWorkerRuntime, WorkerBridgeRuntime
from modulo.worker.transport import InProcessWorkerHTTPTransport


class FakeSmokeTestRunner:
    def run_smoke_test(self, user_message: str):
        from modulo.client.app import SmokeTestResult

        return SmokeTestResult(
            ok=True,
            model_id="llama3.1:8b",
            user_message=user_message,
            response_text="smoke ok",
        )


class FakeOllamaDiscovery:
    def discover(self) -> OllamaDiscoveryStatus:
        return OllamaDiscoveryStatus(
            available=True,
            installed_model_ids=("llama3.1:8b", "qwen3.5:4b"),
            summary="Ollama is available with 1 local model.",
            details="fake discovery",
        )


class FakeHostingRuntimeProbe:
    def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
        return HostingRuntimeProbeStatus(
            reachable=True,
            model_ready=True,
            summary=f"Ollama runtime resolved {model_id} successfully.",
            detail="fake runtime probe",
        )


class CountingOllamaDiscovery:
    def __init__(self) -> None:
        self.calls = 0

    def discover(self) -> OllamaDiscoveryStatus:
        self.calls += 1
        return OllamaDiscoveryStatus(
            available=True,
            installed_model_ids=("llama3.1:8b",),
            summary="counting discovery",
            details="counting discovery",
        )


class CountingHostingRuntimeProbe:
    def __init__(self) -> None:
        self.calls = 0

    def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
        self.calls += 1
        return HostingRuntimeProbeStatus(
            reachable=True,
            model_ready=True,
            summary=f"counting runtime probe for {model_id}",
            detail="counting runtime probe",
        )


class FakeOpenClawDiscovery:
    def discover(self) -> OpenClawDiscoveryStatus:
        return OpenClawDiscoveryStatus(
            installed=False,
            config_present=False,
            configured_for_modulo=False,
            state="not_installed",
            summary="OpenClaw was not detected on this machine.",
            details="No OpenClaw install or config footprint was found.",
        )


class FakeSessionBridge:
    def fetch_platform_status(self) -> PlatformSessionStatus:
        return PlatformSessionStatus(
            connected=True,
            summary="Platform session is connected.",
            details="fake session bridge",
            account_summary="Prototype account: local-dev-user",
            network_models=(
                PlatformModelListing(
                    model_id="network/llama3.1:8b",
                    display_name="Network Llama 3.1 8B",
                    source="network",
                    summary="Advertised by the Modulo network.",
                ),
            ),
            cloud_models=(
                PlatformModelListing(
                    model_id="cloud/gpt-4.1-mini",
                    display_name="Cloud GPT-4.1 Mini",
                    source="cloud",
                    summary="Available through trusted cloud routing.",
                ),
            ),
            credits_summary="12.5 credits available",
            buyer_routing_summary="Buyer routing defaults to platform-managed selection.",
            buyer_config_summary="Buyer config is using platform-managed model selection.",
        )


class ClientWorkerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InMemoryModuloService(router=TrustRouter())
        self.executor = InMemoryWorkerRuntime()
        self.executor.register_worker("worker-1", "hello from worker-1")
        self.app = ModuloHTTPApp(
            service=self.service,
            runtime=InMemoryWorkerRuntime(),
        )
        self.transport = InProcessWorkerHTTPTransport(
            app=self.app,
            config=WorkerBridgeConfig(
                modulo_url="http://127.0.0.1:8000",
                worker_id="worker-1",
                enabled_models=("llama3.1:8b",),
            ),
        )
        self.bridge = WorkerBridgeRuntime(
            config=self.transport.config,
            transport=self.transport,
            executor=self.executor,
        )
        self.client = ModuloClientSupervisor(
            worker_bridge=self.bridge,
            session_bridge=FakeSessionBridge(),
            openclaw_discovery=FakeOpenClawDiscovery(),
            ollama_discovery=FakeOllamaDiscovery(),
            hosting_runtime_probe=FakeHostingRuntimeProbe(),
        )

    def test_client_can_start_hosting_without_drifting_from_worker_status(self) -> None:
        status = self.client.start_hosting()
        self.assertTrue(status.hosting_enabled)
        self.assertIsNotNone(status.worker)
        self.assertEqual("worker-1", status.worker.worker_id)
        self.assertTrue(status.worker.registered_with_cloud)
        self.assertEqual(WorkerRuntimeState.IDLE, status.worker.runtime_state)

    def test_worker_cycle_completes_claimed_job_and_updates_client_status(self) -> None:
        self.client.start_hosting()
        job = self.service.submit_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                messages=(ChatMessage(role="user", content="hello bridge"),),
            )
        )

        status = self.client.run_hosting_cycle()

        self.assertIsNotNone(status.worker)
        self.assertEqual(JobStatus.COMPLETED, status.worker.last_job_status)
        self.assertEqual(1, status.worker.completed_jobs)

        completed_job = self.service.get_job(job.job_id)
        self.assertIsNotNone(completed_job)
        self.assertEqual(JobStatus.COMPLETED, completed_job.status)
        self.assertEqual("hello from worker-1", completed_job.response_text)
        self.assertEqual("hello bridge", completed_job.request.messages[0].content)

    def test_worker_failure_surfaces_through_shared_status_contract(self) -> None:
        self.bridge = WorkerBridgeRuntime(
            config=WorkerBridgeConfig(
                modulo_url="http://127.0.0.1:8000",
                worker_id="worker-2",
                enabled_models=("llama3.1:8b",),
            ),
            transport=InProcessWorkerHTTPTransport(
                app=self.app,
                config=WorkerBridgeConfig(
                    modulo_url="http://127.0.0.1:8000",
                    worker_id="worker-2",
                    enabled_models=("llama3.1:8b",),
                ),
            ),
            executor=InMemoryWorkerRuntime(),
        )
        self.client = ModuloClientSupervisor(worker_bridge=self.bridge)
        self.client.start_hosting()

        job = self.service.submit_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                messages=(ChatMessage(role="user", content="hello failure"),),
            )
        )
        status = self.client.run_hosting_cycle()

        self.assertIsNotNone(status.worker)
        self.assertEqual(WorkerRuntimeState.ERROR, status.worker.runtime_state)
        self.assertFalse(status.worker.healthy)
        self.assertEqual(JobStatus.FAILED, status.worker.last_job_status)
        self.assertEqual(1, status.worker.failed_jobs)
        self.assertIn("No execution adapter", status.worker.last_error)

        failed_job = self.service.get_job(job.job_id)
        self.assertIsNotNone(failed_job)
        self.assertEqual(JobStatus.FAILED, failed_job.status)

    def test_client_onboarding_status_reflects_worker_and_smoke_test_state(self) -> None:
        self.client.smoke_test_runner = FakeSmokeTestRunner()
        self.client.configure_openclaw()
        self.client.start_hosting()
        self.client.run_smoke_test("hello smoke")

        onboarding = self.client.get_onboarding_status()

        self.assertTrue(onboarding.connected_to_modulo)
        self.assertTrue(onboarding.openclaw_configured)
        self.assertTrue(onboarding.hosting_enabled)
        self.assertTrue(onboarding.worker_registered)
        self.assertTrue(onboarding.worker_healthy)
        self.assertTrue(onboarding.smoke_test_ok)
        self.assertEqual("", onboarding.smoke_test_error)

    def test_openclaw_status_distinguishes_installed_unconfigured_state(self) -> None:
        class InstalledOpenClawDiscovery:
            def discover(self) -> OpenClawDiscoveryStatus:
                return OpenClawDiscoveryStatus(
                    installed=True,
                    config_present=True,
                    configured_for_modulo=False,
                    state="installed_unconfigured",
                    summary="OpenClaw is installed, but the local config is not routing through Modulo.",
                    details="Config path: C:\\Users\\test\\.openclaw\\openclaw.json",
                )

        self.client.openclaw_discovery = InstalledOpenClawDiscovery()

        status = self.client.get_status()

        self.assertFalse(status.openclaw.configured)
        self.assertTrue(status.openclaw.installed)
        self.assertTrue(status.openclaw.config_present)
        self.assertEqual("installed_unconfigured", status.openclaw.state)
        self.assertIn("not routing through Modulo", status.openclaw.summary)

    def test_configure_worker_keeps_transport_and_status_in_sync(self) -> None:
        self.client.start_hosting()

        status = self.client.set_hosting_model("llama3.1:8b")

        self.assertEqual(("llama3.1:8b",), self.bridge.config.enabled_models)
        self.assertEqual(("llama3.1:8b",), self.transport.config.enabled_models)
        self.assertTrue(status.hosting_enabled)
        self.assertIsNotNone(status.hosting_setup)
        self.assertEqual("llama3.1:8b", status.hosting_setup.selected_model_id)

    def test_client_status_includes_session_bridge_platform_state(self) -> None:
        status = self.client.get_status()

        self.assertTrue(status.platform.connected)
        self.assertEqual("Platform session is connected.", status.platform.summary)
        self.assertIn("local-dev-user", status.platform.account_summary)
        self.assertEqual(1, len(status.platform.network_models))
        self.assertEqual("network", status.platform.network_models[0].source)
        self.assertEqual(1, len(status.platform.cloud_models))
        self.assertIn("credits", status.platform.credits_summary)
        self.assertIn("platform-managed", status.platform.buyer_config_summary)
        self.assertIsNotNone(status.worker)

    def test_hosting_setup_includes_ollama_discovery_state(self) -> None:
        status = self.client.get_status()

        self.assertTrue(status.hosting_setup.ollama_available)
        self.assertEqual(("llama3.1:8b", "qwen3.5:4b"), status.hosting_setup.installed_model_ids)
        self.assertEqual(("llama3.1:8b",), status.hosting_setup.supported_installed_model_ids)
        self.assertEqual((), status.hosting_setup.supported_missing_model_ids)
        self.assertEqual(("qwen3.5:4b",), status.hosting_setup.unsupported_installed_model_ids)
        self.assertTrue(status.hosting_setup.preflight.ok)
        self.assertEqual("", status.hosting_setup.preflight.failure_reason)
        self.assertTrue(status.hosting_setup.can_enable_hosting)
        self.assertIn("Readiness result: Hosting preflight passed", status.hosting_setup.readiness_details)
        self.assertIn("Ollama is available", status.hosting_setup.readiness_details)

    def test_hosting_preflight_fails_when_selected_model_is_missing(self) -> None:
        class MissingModelDiscovery:
            def discover(self) -> OllamaDiscoveryStatus:
                return OllamaDiscoveryStatus(
                    available=True,
                    installed_model_ids=("qwen3.5:4b",),
                    summary="Ollama is available with 1 local model.",
                    details="missing selected model",
                )

        self.client.ollama_discovery = MissingModelDiscovery()

        status = self.client.get_status()

        self.assertFalse(status.hosting_setup.preflight.ok)
        self.assertIn("not installed locally", status.hosting_setup.preflight.summary)
        self.assertEqual("llama3.1:8b", status.hosting_setup.preflight.failure_reason)
        self.assertTrue(status.hosting_setup.prototype_hosting_available)
        self.assertTrue(status.hosting_setup.can_enable_hosting)

    def test_hosting_preflight_fails_when_runtime_probe_cannot_resolve_model(self) -> None:
        class FailingRuntimeProbe:
            def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
                return HostingRuntimeProbeStatus(
                    reachable=False,
                    model_ready=False,
                    summary=f"runtime failed for {model_id}",
                    detail="runtime probe failed",
                    error="runtime probe failed",
                )

        self.client.hosting_runtime_probe = FailingRuntimeProbe()

        status = self.client.get_status()

        self.assertFalse(status.hosting_setup.preflight.ok)
        self.assertIn("could not resolve", status.hosting_setup.preflight.summary)
        self.assertEqual("runtime probe failed", status.hosting_setup.preflight.failure_reason)

    def test_readiness_checks_are_cached_between_status_reads(self) -> None:
        discovery = CountingOllamaDiscovery()
        runtime_probe = CountingHostingRuntimeProbe()
        self.client.ollama_discovery = discovery
        self.client.hosting_runtime_probe = runtime_probe

        self.client.get_status()
        self.client.get_status()

        self.assertEqual(1, discovery.calls)
        self.assertEqual(1, runtime_probe.calls)


if __name__ == "__main__":
    unittest.main()
