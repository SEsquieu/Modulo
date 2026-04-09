import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.common.contracts import ChatRequest, JobStatus, WorkerKind, WorkerModelState, WorkerSnapshot, ExecutionMode
from modulo.cloud.http import ModuloHTTPApp
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService
from modulo.worker.runtime import InMemoryWorkerRuntime


class ModuloHTTPAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InMemoryModuloService(router=TrustRouter())
        self.runtime = InMemoryWorkerRuntime()
        self.app = ModuloHTTPApp(service=self.service, runtime=self.runtime)

        self.service.register_worker(
            WorkerSnapshot(
                worker_id="network-1",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                    ),
                ),
            )
        )
        self.runtime.register_worker("network-1", "hello from modulo")

    def test_get_tags_returns_supported_models(self) -> None:
        status, payload = self.app.handle("GET", "/api/tags")
        self.assertEqual(200, status)
        self.assertEqual("llama3.1:8b", payload["models"][0]["name"])

    def test_get_tags_includes_healthy_advertised_uncurated_models(self) -> None:
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="network-qwen",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="qwen3.5:4b",
                        runtime_identity="qwen3.5:4b",
                    ),
                ),
            )
        )

        status, payload = self.app.handle("GET", "/api/tags")

        self.assertEqual(200, status)
        advertised_ids = {model["name"] for model in payload["models"]}
        self.assertIn("qwen3.5:4b", advertised_ids)

    def test_post_chat_returns_ollama_shaped_response(self) -> None:
        status, payload = self.app.handle(
            "POST",
            "/api/chat",
            json.dumps(
                {
                    "model": "llama3.1:8b",
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                }
            ).encode("utf-8"),
        )
        self.assertEqual(200, status)
        self.assertEqual("llama3.1:8b", payload["model"])
        self.assertEqual("assistant", payload["message"]["role"])
        self.assertEqual("hello from modulo", payload["message"]["content"])
        self.assertTrue(payload["done"])

    def test_post_chat_rejects_missing_model(self) -> None:
        status, payload = self.app.handle(
            "POST",
            "/api/chat",
            json.dumps({"messages": [{"role": "user", "content": "hi"}]}).encode("utf-8"),
        )
        self.assertEqual(400, status)
        self.assertIn("model", payload["error"])

    def test_post_chat_returns_gateway_error_when_runtime_missing(self) -> None:
        self.runtime = InMemoryWorkerRuntime()
        self.app = ModuloHTTPApp(service=self.service, runtime=self.runtime)

        status, payload = self.app.handle(
            "POST",
            "/api/chat",
            json.dumps({"model": "llama3.1:8b", "messages": []}).encode("utf-8"),
        )
        self.assertEqual(502, status)
        self.assertIn("No execution adapter", payload["error"])

    def test_worker_register_endpoint_adds_worker(self) -> None:
        status, payload = self.app.handle(
            "POST",
            "/worker/register",
            json.dumps(
                {
                    "worker_id": "cloud-1",
                    "kind": "cloud",
                    "max_concurrency": 2,
                    "models": ["llama3.1:8b"],
                }
            ).encode("utf-8"),
        )
        self.assertEqual(200, status)
        self.assertEqual("registered", payload["status"])
        self.assertIsNotNone(self.service.registry.get("cloud-1"))

    def test_worker_heartbeat_updates_health_and_load(self) -> None:
        status, payload = self.app.handle(
            "POST",
            "/worker/heartbeat",
            json.dumps(
                {
                    "worker_id": "network-1",
                    "healthy": False,
                    "current_load": 1,
                }
            ).encode("utf-8"),
        )
        self.assertEqual(200, status)
        self.assertFalse(payload["healthy"])

        worker = self.service.registry.get("network-1")
        self.assertIsNotNone(worker)
        self.assertFalse(worker.healthy)
        self.assertEqual(1, worker.advertised_models[0].current_load)

    def test_worker_claim_result_flow(self) -> None:
        job = self.service.submit_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )
        claim_status, claim_payload = self.app.handle(
            "POST",
            "/worker/jobs/claim",
            json.dumps({"worker_id": "network-1"}).encode("utf-8"),
        )
        self.assertEqual(200, claim_status)
        self.assertEqual(job.job_id, claim_payload["job"]["job_id"])

        result_status, result_payload = self.app.handle(
            "POST",
            f"/worker/jobs/{job.job_id}/result",
            json.dumps({"worker_id": "network-1", "response_text": "worker result"}).encode("utf-8"),
        )
        self.assertEqual(200, result_status)
        self.assertEqual("completed", result_payload["status"])

        completed_job = self.service.get_job(job.job_id)
        self.assertIsNotNone(completed_job)
        self.assertEqual(JobStatus.COMPLETED, completed_job.status)
        self.assertEqual("worker result", completed_job.response_text)

    def test_worker_claim_fail_flow(self) -> None:
        job = self.service.submit_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )
        self.app.handle(
            "POST",
            "/worker/jobs/claim",
            json.dumps({"worker_id": "network-1"}).encode("utf-8"),
        )

        fail_status, fail_payload = self.app.handle(
            "POST",
            f"/worker/jobs/{job.job_id}/fail",
            json.dumps(
                {
                    "worker_id": "network-1",
                    "error_code": "EXEC_TIMEOUT",
                    "message": "Execution timed out",
                }
            ).encode("utf-8"),
        )
        self.assertEqual(200, fail_status)
        self.assertEqual("failed", fail_payload["status"])

        failed_job = self.service.get_job(job.job_id)
        self.assertIsNotNone(failed_job)
        self.assertEqual(JobStatus.FAILED, failed_job.status)
        self.assertIn("EXEC_TIMEOUT", failed_job.failure_reason)


if __name__ == "__main__":
    unittest.main()
