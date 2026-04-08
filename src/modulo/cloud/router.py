from __future__ import annotations

from dataclasses import dataclass

from modulo.common.catalog import get_model
from modulo.common.contracts import (
    ChatRequest,
    ExecutionMode,
    RouteDecision,
    WorkerKind,
    WorkerSnapshot,
)
from modulo.common.policy import V1Policy, V1_DEFAULT_POLICY


class RoutingError(Exception):
    """Raised when a request cannot be routed under the current policy."""


@dataclass
class TrustRouter:
    policy: V1Policy = V1_DEFAULT_POLICY

    def route(
        self,
        request: ChatRequest,
        workers: list[WorkerSnapshot],
        *,
        exclude_worker_ids: set[str] | None = None,
    ) -> RouteDecision:
        model = get_model(request.model_id)
        if self.policy.require_curated_supported_model and model is None:
            raise RoutingError(f"Unsupported model for v1: {request.model_id}")

        if request.stream and not self.policy.streaming_enabled:
            raise RoutingError("Streaming is intentionally disabled in v1.")

        if request.requires_tools and not self.policy.tool_calling_enabled:
            raise RoutingError("Tool calling is intentionally disabled in v1.")

        mode_candidates = self._filter_for_mode(
            request.execution_mode,
            request.model_id,
            workers,
            exclude_worker_ids=exclude_worker_ids,
        )
        if mode_candidates:
            winner = mode_candidates[0]
            return RouteDecision(
                worker_id=winner.worker_id,
                worker_kind=winner.kind,
                model_id=request.model_id,
                execution_mode=request.execution_mode,
                reason="Selected highest-trust healthy worker for requested mode.",
            )

        if (
            request.execution_mode is ExecutionMode.NETWORK
            and self.policy.allow_trusted_cloud_fallback_for_exact_match
        ):
            fallback_candidates = self._filter_for_mode(
                ExecutionMode.CLOUD,
                request.model_id,
                workers,
                exclude_worker_ids=exclude_worker_ids,
            )
            if fallback_candidates:
                winner = fallback_candidates[0]
                return RouteDecision(
                    worker_id=winner.worker_id,
                    worker_kind=winner.kind,
                    model_id=request.model_id,
                    execution_mode=ExecutionMode.CLOUD,
                    routed_via_fallback=True,
                    reason="Network had no eligible worker; exact-model cloud fallback selected.",
                )

        raise RoutingError("No eligible execution target found.")

    def _filter_for_mode(
        self,
        mode: ExecutionMode,
        model_id: str,
        workers: list[WorkerSnapshot],
        *,
        exclude_worker_ids: set[str] | None = None,
    ) -> list[WorkerSnapshot]:
        eligible_kind = {
            ExecutionMode.LOCAL: WorkerKind.LOCAL,
            ExecutionMode.NETWORK: WorkerKind.NETWORK,
            ExecutionMode.CLOUD: WorkerKind.CLOUD,
        }[mode]

        eligible_workers: list[tuple[float, WorkerSnapshot]] = []
        for worker in workers:
            if exclude_worker_ids and worker.worker_id in exclude_worker_ids:
                continue
            if worker.kind is not eligible_kind or not worker.healthy:
                continue

            model_state = worker.supports_model(model_id)
            if model_state is None:
                continue

            if model_state.current_load >= worker.max_concurrency:
                continue

            score = self._score_worker(worker.worker_id, worker.max_concurrency, model_state)
            eligible_workers.append((score, worker))

        eligible_workers.sort(key=lambda item: item[0], reverse=True)
        return [worker for _, worker in eligible_workers]

    @staticmethod
    def _score_worker(worker_id: str, max_concurrency: int, model_state) -> float:
        del worker_id
        headroom = max(max_concurrency - model_state.current_load, 0)
        return (
            model_state.confidence * 0.50
            + model_state.recent_success_rate * 0.35
            + (1.0 - model_state.timeout_rate) * 0.10
            + headroom * 0.05
        )
