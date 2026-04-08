import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.common.contracts import (
    ChatRequest,
    ExecutionMode,
    JobFailure,
    JobResult,
    JobStatus,
    RoutingPolicy,
    WorkerKind,
    WorkerModelState,
    WorkerSnapshot,
)
from modulo.cloud.jobs import JobQueueError
from modulo.cloud.router import RoutingError, TrustRouter
from modulo.cloud.runtime import InMemoryModuloService


class TrustRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = TrustRouter()
        self.service = InMemoryModuloService(router=self.router)

    def test_routes_to_best_network_worker(self) -> None:
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="network-low",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                        confidence=0.70,
                        recent_success_rate=0.80,
                    ),
                ),
            )
        )
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="network-high",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=2,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                        confidence=0.95,
                        recent_success_rate=0.95,
                    ),
                ),
            )
        )

        decision = self.service.route_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                routing_policy=RoutingPolicy.STRICT,
            )
        )
        self.assertEqual("network-high", decision.worker_id)
        self.assertFalse(decision.routed_via_fallback)

    def test_falls_back_to_exact_match_cloud_worker(self) -> None:
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="cloud-1",
                kind=WorkerKind.CLOUD,
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

        decision = self.service.route_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )
        self.assertTrue(decision.routed_via_fallback)
        self.assertEqual(ExecutionMode.CLOUD, decision.execution_mode)

    def test_rejects_unsupported_model(self) -> None:
        with self.assertRaises(RoutingError):
            self.service.route_chat(
                ChatRequest(model_id="qwen2.5-coder:7b", execution_mode=ExecutionMode.NETWORK)
            )

    def test_rejects_streaming_in_v1(self) -> None:
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

        with self.assertRaises(RoutingError):
            self.service.route_chat(
                ChatRequest(
                    model_id="llama3.1:8b",
                    execution_mode=ExecutionMode.NETWORK,
                    stream=True,
                )
            )

    def test_submit_claim_and_complete_job(self) -> None:
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

        job = self.service.submit_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )
        self.assertEqual(JobStatus.PENDING, job.status)

        claim = self.service.claim_job("network-1")
        self.assertIsNotNone(claim)
        self.assertEqual(job.job_id, claim.job_id)

        completed = self.service.complete_job(
            JobResult(
                job_id=job.job_id,
                worker_id="network-1",
                response_text="hello from worker",
            )
        )
        self.assertEqual(JobStatus.COMPLETED, completed.status)
        self.assertEqual("hello from worker", completed.response_text)

    def test_submit_and_fail_job(self) -> None:
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

        job = self.service.submit_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )
        self.service.claim_job("network-1")
        failed = self.service.fail_job(
            JobFailure(
                job_id=job.job_id,
                worker_id="network-1",
                error_code="EXEC_TIMEOUT",
                message="Execution timed out",
            )
        )
        self.assertEqual(JobStatus.FAILED, failed.status)
        self.assertIn("EXEC_TIMEOUT", failed.failure_reason)

    def test_failure_retries_once_on_another_eligible_worker(self) -> None:
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
                        confidence=0.95,
                    ),
                ),
            )
        )
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="network-2",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                        confidence=0.90,
                    ),
                ),
            )
        )

        job = self.service.submit_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )
        self.service.claim_job("network-1")

        retried = self.service.fail_job(
            JobFailure(
                job_id=job.job_id,
                worker_id="network-1",
                error_code="EXEC_TIMEOUT",
                message="Execution timed out",
            )
        )

        self.assertEqual(JobStatus.PENDING, retried.status)
        self.assertEqual("network-2", retried.assigned_worker_id)
        self.assertEqual(2, retried.attempts)

        unhealthy_worker = self.service.registry.get("network-1")
        self.assertIsNotNone(unhealthy_worker)
        self.assertFalse(unhealthy_worker.healthy)

    def test_timeout_marks_worker_unhealthy_and_fails_cleanly_when_no_retry_target(self) -> None:
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

        job = self.service.submit_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )
        self.service.claim_job("network-1")

        timed_out = self.service.timeout_job(job.job_id, "network-1")

        self.assertEqual(JobStatus.FAILED, timed_out.status)
        self.assertIn("EXEC_TIMEOUT", timed_out.failure_reason)

        unhealthy_worker = self.service.registry.get("network-1")
        self.assertIsNotNone(unhealthy_worker)
        self.assertFalse(unhealthy_worker.healthy)

    def test_job_cannot_be_completed_by_wrong_worker(self) -> None:
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

        job = self.service.submit_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )
        self.service.claim_job("network-1")

        with self.assertRaises(JobQueueError):
            self.service.complete_job(
                JobResult(
                    job_id=job.job_id,
                    worker_id="network-2",
                    response_text="wrong worker",
                )
            )


if __name__ == "__main__":
    unittest.main()
