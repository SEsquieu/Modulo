import threading
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.cloud.http import build_http_server
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService
from modulo.common.contracts import (
    ChatMessage,
    ChatRequest,
    ExecutionMode,
    JobStatus,
    RouteScope,
    WorkerBridgeConfig,
    WorkerRuntimeState,
)
from modulo.worker.runtime import InMemoryWorkerRuntime, WorkerBridgeRuntime
from modulo.worker.transport import UrllibWorkerHTTPTransport


class UrllibWorkerHTTPTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InMemoryModuloService(router=TrustRouter())
        self.cloud_runtime = InMemoryWorkerRuntime()
        self.server = build_http_server(
            "127.0.0.1",
            0,
            service=self.service,
            runtime=self.cloud_runtime,
        )
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2.0)

    def test_worker_bridge_can_run_against_real_http_endpoint(self) -> None:
        executor = InMemoryWorkerRuntime()
        executor.register_worker("worker-http", "hello over real http")
        config = WorkerBridgeConfig(
            modulo_url=self.base_url,
            worker_id="worker-http",
            enabled_models=("llama3.1:8b",),
            serving_scope=RouteScope.PRIVATE,
            private_network_id="org-a",
        )
        bridge = WorkerBridgeRuntime(
            config=config,
            transport=UrllibWorkerHTTPTransport(config=config, timeout_seconds=2.0),
            executor=executor,
        )

        started = bridge.start()

        self.assertTrue(started.registered_with_cloud)
        registered_worker = self.service.registry.get("worker-http")
        self.assertIsNotNone(registered_worker)
        self.assertEqual(RouteScope.PRIVATE, registered_worker.resolved_scope())
        self.assertEqual("org-a", registered_worker.private_network_id)

        job = self.service.submit_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                requested_scope=RouteScope.PRIVATE,
                private_network_id="org-a",
                messages=(ChatMessage(role="user", content="hello bridge"),),
            )
        )

        status = bridge.run_cycle()

        self.assertEqual(WorkerRuntimeState.IDLE, status.runtime_state)
        self.assertEqual(JobStatus.COMPLETED, status.last_job_status)
        self.assertEqual(1, status.completed_jobs)
        completed = self.service.get_job(job.job_id)
        self.assertIsNotNone(completed)
        self.assertEqual(JobStatus.COMPLETED, completed.status)
        self.assertEqual("hello over real http", completed.response_text)

        traces = self.service.list_traces()
        self.assertEqual(1, len(traces))
        self.assertEqual(job.trace_id, traces[0].trace_id)
        self.assertEqual("completed", traces[0].final_status)
        self.assertEqual("worker-http", traces[0].selected_worker_id)

    def test_claim_job_over_real_http_preserves_trace_and_scope(self) -> None:
        executor = InMemoryWorkerRuntime()
        executor.register_worker("worker-http", "hello over real http")
        config = WorkerBridgeConfig(
            modulo_url=self.base_url,
            worker_id="worker-http",
            enabled_models=("llama3.1:8b",),
            serving_scope=RouteScope.PRIVATE,
            private_network_id="org-a",
        )
        transport = UrllibWorkerHTTPTransport(config=config, timeout_seconds=2.0)
        transport.register_worker()

        job = self.service.submit_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                requested_scope=RouteScope.PRIVATE,
                private_network_id="org-a",
                messages=(ChatMessage(role="user", content="hello trace"),),
            )
        )

        claim = transport.claim_job("worker-http")

        self.assertIsNotNone(claim)
        assert claim is not None
        self.assertEqual(job.job_id, claim.job_id)
        self.assertEqual(job.trace_id, claim.trace_id)
        self.assertEqual(RouteScope.PRIVATE, claim.request.resolved_scope())
        self.assertEqual("org-a", claim.request.private_network_id)
        self.assertEqual("hello trace", claim.request.messages[0].content)

    def test_worker_bridge_surfaces_unreachable_modulo_url_cleanly(self) -> None:
        config = WorkerBridgeConfig(
            modulo_url="http://127.0.0.1:9",
            worker_id="worker-http",
            enabled_models=("llama3.1:8b",),
        )
        bridge = WorkerBridgeRuntime(
            config=config,
            transport=UrllibWorkerHTTPTransport(config=config, timeout_seconds=0.2),
            executor=InMemoryWorkerRuntime(),
        )

        status = bridge.start()

        self.assertEqual(WorkerRuntimeState.ERROR, status.runtime_state)
        self.assertFalse(status.registered_with_cloud)
        self.assertIn("Failed to register worker", status.last_error)


if __name__ == "__main__":
    unittest.main()
