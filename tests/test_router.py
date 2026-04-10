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
    RouteScope,
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

    def test_private_scope_routes_only_matching_private_network(self) -> None:
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="private-a",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                        confidence=0.80,
                    ),
                ),
                serving_scope=RouteScope.PRIVATE,
                private_network_id="org-a",
            )
        )
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="private-b",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                        confidence=0.99,
                    ),
                ),
                serving_scope=RouteScope.PRIVATE,
                private_network_id="org-b",
            )
        )

        decision = self.service.route_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                requested_scope=RouteScope.PRIVATE,
                private_network_id="org-a",
            )
        )

        self.assertEqual("private-a", decision.worker_id)

    def test_private_scope_rejects_public_scope_worker_even_with_higher_score(self) -> None:
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="private-1",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                        confidence=0.80,
                    ),
                ),
                serving_scope=RouteScope.PRIVATE,
                private_network_id="org-a",
            )
        )
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="public-1",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                        confidence=0.99,
                    ),
                ),
                serving_scope=RouteScope.PUBLIC,
            )
        )

        decision = self.service.route_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                requested_scope=RouteScope.PRIVATE,
                private_network_id="org-a",
            )
        )

        self.assertEqual("private-1", decision.worker_id)

    def test_route_trace_records_scope_selection_and_filtered_workers(self) -> None:
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="private-1",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                        confidence=0.80,
                    ),
                ),
                serving_scope=RouteScope.PRIVATE,
                private_network_id="org-a",
            )
        )
        self.service.register_worker(
            WorkerSnapshot(
                worker_id="public-1",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                        confidence=0.99,
                    ),
                ),
                serving_scope=RouteScope.PUBLIC,
            )
        )

        job = self.service.submit_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                requested_scope=RouteScope.PRIVATE,
                private_network_id="org-a",
            )
        )
        self.service.claim_job("private-1")
        self.service.complete_job(
            JobResult(
                job_id=job.job_id,
                worker_id="private-1",
                response_text="private response",
            )
        )

        traces = self.service.list_traces()
        self.assertEqual(1, len(traces))
        trace = traces[0]
        self.assertEqual(RouteScope.PRIVATE, trace.resolved_scope)
        self.assertEqual("org-a", trace.private_network_id)
        self.assertEqual(job.job_id, trace.job_id)
        self.assertEqual(("private-1",), trace.eligible_worker_ids)
        self.assertEqual("private-1", trace.selected_worker_id)
        self.assertEqual("selected_requested_mode", trace.route_reason_code)
        self.assertEqual("completed", trace.final_status)
        self.assertTrue(
            any(
                item.worker_id == "public-1"
                and item.reason_code in {"scope_mismatch", "private_network_mismatch"}
                for item in trace.filtered_worker_reasons
            )
        )

    def test_routes_exact_match_worker_for_uncurated_advertised_model(self) -> None:
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

        decision = self.service.route_chat(
            ChatRequest(model_id="qwen3.5:4b", execution_mode=ExecutionMode.NETWORK)
        )

        self.assertEqual("network-qwen", decision.worker_id)
        self.assertEqual("qwen3.5:4b", decision.model_id)

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

    def test_route_trace_records_retry_as_separate_attempt(self) -> None:
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
        self.service.claim_job("network-2")
        self.service.complete_job(
            JobResult(
                job_id=job.job_id,
                worker_id="network-2",
                response_text="retried response",
            )
        )

        traces = sorted(self.service.list_traces(), key=lambda item: item.attempt_number)
        self.assertEqual(2, len(traces))
        first_trace, second_trace = traces
        self.assertEqual(1, first_trace.attempt_number)
        self.assertEqual("network-1", first_trace.selected_worker_id)
        self.assertEqual("retried", first_trace.final_status)
        self.assertIn("EXEC_TIMEOUT", first_trace.final_error)
        self.assertEqual(2, second_trace.attempt_number)
        self.assertEqual(1, second_trace.retry_count)
        self.assertEqual(retried.trace_id, second_trace.trace_id)
        self.assertEqual("network-2", second_trace.selected_worker_id)
        self.assertEqual("completed", second_trace.final_status)

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

    def test_same_buyer_prefers_leased_worker_over_new_higher_score(self) -> None:
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
                        confidence=0.80,
                    ),
                ),
            )
        )

        first_job = self.service.submit_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                buyer_id="buyer-1",
            )
        )
        self.service.claim_job("network-1")
        self.service.complete_job(
            JobResult(
                job_id=first_job.job_id,
                worker_id="network-1",
                response_text="first response",
            )
        )

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
                        confidence=0.70,
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
                        confidence=0.99,
                    ),
                ),
            )
        )

        same_buyer_decision = self.service.route_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                buyer_id="buyer-1",
            )
        )
        other_buyer_decision = self.service.route_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                buyer_id="buyer-2",
            )
        )

        self.assertEqual("network-1", same_buyer_decision.worker_id)
        self.assertIn("leased worker", same_buyer_decision.reason)
        self.assertEqual("network-2", other_buyer_decision.worker_id)

    def test_lease_expires_after_inactivity(self) -> None:
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
                        confidence=0.80,
                    ),
                ),
            )
        )

        first_job = self.service.submit_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                buyer_id="buyer-lease",
            )
        )
        self.service.claim_job("network-1")
        self.service.complete_job(
            JobResult(
                job_id=first_job.job_id,
                worker_id="network-1",
                response_text="first response",
            )
        )

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
                        confidence=0.70,
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
                        confidence=0.99,
                    ),
                ),
            )
        )

        for index in range(4):
            self.service.route_chat(
                ChatRequest(
                    model_id="llama3.1:8b",
                    execution_mode=ExecutionMode.NETWORK,
                    buyer_id=f"other-buyer-{index}",
                )
            )

        expired_decision = self.service.route_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                buyer_id="buyer-lease",
            )
        )

        self.assertEqual("network-2", expired_decision.worker_id)

    def test_failed_worker_breaks_buyer_lease_and_retry_rehomes_buyer(self) -> None:
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
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                buyer_id="buyer-rehome",
            )
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

        next_decision = self.service.route_chat(
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                buyer_id="buyer-rehome",
            )
        )

        self.assertEqual("network-2", retried.assigned_worker_id)
        self.assertEqual("network-2", next_decision.worker_id)

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
