import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.common.contracts import (
    ChatRequest,
    ExecutionMode,
    RoutingPolicy,
    WorkerKind,
    WorkerModelState,
    WorkerSnapshot,
)
from modulo.service.router import RoutingError, TrustRouter
from modulo.service.runtime import InMemoryModuloService


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


if __name__ == "__main__":
    unittest.main()
