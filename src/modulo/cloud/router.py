from __future__ import annotations

from dataclasses import dataclass

from modulo.common.catalog import get_model
from modulo.common.contracts import (
    ChatRequest,
    ExecutionMode,
    FilteredWorkerReason,
    RouteScope,
    RouteDecision,
    WorkerKind,
    WorkerSnapshot,
)
from modulo.common.policy import V1Policy, V1_DEFAULT_POLICY


class RoutingError(Exception):
    """Raised when a request cannot be routed under the current policy."""


@dataclass(frozen=True)
class RouteTraceDraft:
    decision: RouteDecision | None
    resolved_scope: RouteScope
    eligible_worker_ids: tuple[str, ...]
    filtered_worker_reasons: tuple[FilteredWorkerReason, ...]
    route_reason_code: str = ""
    continuity_used: bool = False
    warm_path_used: bool = False
    error_message: str = ""


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
        trace = self.trace_route(
            request=request,
            workers=workers,
            exclude_worker_ids=exclude_worker_ids,
        )
        if trace.decision is None:
            raise RoutingError(trace.error_message or "No eligible execution target found.")
        return trace.decision

    def trace_route(
        self,
        request: ChatRequest,
        workers: list[WorkerSnapshot],
        *,
        exclude_worker_ids: set[str] | None = None,
    ) -> RouteTraceDraft:
        model = get_model(request.model_id)
        if (
            self.policy.require_curated_supported_model
            and model is None
            and not self._has_advertised_exact_match(request.model_id, workers)
        ):
            return RouteTraceDraft(
                decision=None,
                resolved_scope=self._resolve_request_scope(request.execution_mode, request),
                eligible_worker_ids=(),
                filtered_worker_reasons=(),
                route_reason_code="unsupported_model",
                error_message=f"Unsupported model for v1: {request.model_id}",
            )

        if request.stream and not self.policy.streaming_enabled:
            return RouteTraceDraft(
                decision=None,
                resolved_scope=self._resolve_request_scope(request.execution_mode, request),
                eligible_worker_ids=(),
                filtered_worker_reasons=(),
                route_reason_code="streaming_disabled",
                error_message="Streaming is intentionally disabled in v1.",
            )

        if request.requires_tools and not self.policy.tool_calling_enabled:
            return RouteTraceDraft(
                decision=None,
                resolved_scope=self._resolve_request_scope(request.execution_mode, request),
                eligible_worker_ids=(),
                filtered_worker_reasons=(),
                route_reason_code="tool_calling_disabled",
                error_message="Tool calling is intentionally disabled in v1.",
            )

        mode_candidates, filtered_reasons = self._filter_for_mode(
            request=request,
            mode=request.execution_mode,
            model_id=request.model_id,
            workers=workers,
            exclude_worker_ids=exclude_worker_ids,
        )
        if mode_candidates:
            winner = mode_candidates[0]
            decision = RouteDecision(
                worker_id=winner.worker_id,
                worker_kind=winner.kind,
                model_id=request.model_id,
                execution_mode=request.execution_mode,
                reason="Selected highest-trust healthy worker for requested mode.",
            )
            return RouteTraceDraft(
                decision=decision,
                resolved_scope=self._resolve_request_scope(request.execution_mode, request),
                eligible_worker_ids=tuple(worker.worker_id for worker in mode_candidates),
                filtered_worker_reasons=tuple(filtered_reasons),
                route_reason_code="selected_requested_mode",
            )

        if (
            request.execution_mode is ExecutionMode.NETWORK
            and self.policy.allow_trusted_cloud_fallback_for_exact_match
        ):
            fallback_candidates, fallback_filtered = self._filter_for_mode(
                request=request,
                mode=ExecutionMode.CLOUD,
                model_id=request.model_id,
                workers=workers,
                exclude_worker_ids=exclude_worker_ids,
            )
            if fallback_candidates:
                winner = fallback_candidates[0]
                decision = RouteDecision(
                    worker_id=winner.worker_id,
                    worker_kind=winner.kind,
                    model_id=request.model_id,
                    execution_mode=ExecutionMode.CLOUD,
                    routed_via_fallback=True,
                    reason="Network had no eligible worker; exact-model cloud fallback selected.",
                )
                return RouteTraceDraft(
                    decision=decision,
                    resolved_scope=self._resolve_request_scope(request.execution_mode, request),
                    eligible_worker_ids=tuple(worker.worker_id for worker in fallback_candidates),
                    filtered_worker_reasons=tuple((*filtered_reasons, *fallback_filtered)),
                    route_reason_code="cloud_fallback_exact_match",
                )

        return RouteTraceDraft(
            decision=None,
            resolved_scope=self._resolve_request_scope(request.execution_mode, request),
            eligible_worker_ids=(),
            filtered_worker_reasons=tuple(filtered_reasons),
            route_reason_code="no_eligible_target",
            error_message="No eligible execution target found.",
        )

    def _filter_for_mode(
        self,
        *,
        request: ChatRequest,
        mode: ExecutionMode,
        model_id: str,
        workers: list[WorkerSnapshot],
        exclude_worker_ids: set[str] | None = None,
    ) -> tuple[list[WorkerSnapshot], list[FilteredWorkerReason]]:
        eligible_kind = {
            ExecutionMode.LOCAL: WorkerKind.LOCAL,
            ExecutionMode.NETWORK: WorkerKind.NETWORK,
            ExecutionMode.CLOUD: WorkerKind.CLOUD,
        }[mode]
        request_scope = self._resolve_request_scope(mode, request)

        eligible_workers: list[tuple[float, WorkerSnapshot]] = []
        filtered_reasons: list[FilteredWorkerReason] = []
        for worker in workers:
            if exclude_worker_ids and worker.worker_id in exclude_worker_ids:
                filtered_reasons.append(
                    FilteredWorkerReason(
                        worker_id=worker.worker_id,
                        reason_code="excluded_worker",
                        detail="Worker was explicitly excluded from this routing attempt.",
                    )
                )
                continue
            if worker.kind is not eligible_kind:
                filtered_reasons.append(
                    FilteredWorkerReason(
                        worker_id=worker.worker_id,
                        reason_code="worker_kind_mismatch",
                        detail=f"Worker kind {worker.kind.value} does not match required {eligible_kind.value}.",
                    )
                )
                continue
            if not worker.healthy:
                filtered_reasons.append(
                    FilteredWorkerReason(
                        worker_id=worker.worker_id,
                        reason_code="worker_unhealthy",
                        detail="Worker is not currently healthy.",
                    )
                )
                continue
            if not self._worker_matches_scope(
                request_scope=request_scope,
                request_private_network_id=request.private_network_id,
                worker=worker,
            ):
                reason_code = (
                    "private_network_mismatch"
                    if request_scope is RouteScope.PRIVATE
                    and request.private_network_id
                    and worker.private_network_id != request.private_network_id
                    else "scope_mismatch"
                )
                filtered_reasons.append(
                    FilteredWorkerReason(
                        worker_id=worker.worker_id,
                        reason_code=reason_code,
                        detail=(
                            f"Worker scope {worker.resolved_scope().value}"
                            f" does not match request scope {request_scope.value}."
                        ),
                    )
                )
                continue

            model_state = worker.supports_model(model_id)
            if model_state is None:
                filtered_reasons.append(
                    FilteredWorkerReason(
                        worker_id=worker.worker_id,
                        reason_code="model_not_advertised",
                        detail=f"Worker does not advertise {model_id}.",
                    )
                )
                continue

            if model_state.current_load >= worker.max_concurrency:
                filtered_reasons.append(
                    FilteredWorkerReason(
                        worker_id=worker.worker_id,
                        reason_code="worker_at_capacity",
                        detail="Worker current load meets or exceeds max concurrency.",
                    )
                )
                continue

            score = self._score_worker(worker.worker_id, worker.max_concurrency, model_state)
            eligible_workers.append((score, worker))

        eligible_workers.sort(key=lambda item: item[0], reverse=True)
        return [worker for _, worker in eligible_workers], filtered_reasons

    @staticmethod
    def _has_advertised_exact_match(model_id: str, workers: list[WorkerSnapshot]) -> bool:
        return any(worker.supports_model(model_id) is not None for worker in workers)

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

    @staticmethod
    def _resolve_request_scope(mode: ExecutionMode, request: ChatRequest) -> RouteScope:
        if request.requested_scope is not None:
            return request.requested_scope
        return {
            ExecutionMode.LOCAL: RouteScope.LOCAL,
            ExecutionMode.NETWORK: RouteScope.PRIVATE,
            ExecutionMode.CLOUD: RouteScope.CLOUD,
        }[mode]

    @staticmethod
    def _worker_matches_scope(
        *,
        request_scope: RouteScope,
        request_private_network_id: str,
        worker: WorkerSnapshot,
    ) -> bool:
        worker_scope = worker.resolved_scope()
        if worker_scope is not request_scope:
            return False
        if request_scope is not RouteScope.PRIVATE:
            return True
        if request_private_network_id and worker.private_network_id != request_private_network_id:
            return False
        return True
