from __future__ import annotations

from dataclasses import dataclass, field, replace

from modulo.common.contracts import (
    ChatRequest,
    ExecutionMode,
    JobClaim,
    JobFailure,
    JobRecord,
    JobResult,
    RouteTraceRecord,
    RouteScope,
    RouteDecision,
    WorkerHeartbeat,
    WorkerSnapshot,
)
from modulo.cloud.jobs import InMemoryJobQueue, JobQueueError
from modulo.cloud.registry import InMemoryWorkerRegistry
from modulo.cloud.router import RouteTraceDraft, RoutingError, TrustRouter


@dataclass(frozen=True)
class LeaseRecord:
    buyer_id: str
    model_id: str
    worker_id: str
    execution_mode: ExecutionMode
    expires_at_tick: int


@dataclass
class InMemoryLeaseManager:
    ttl_ticks: int = 3
    _leases: dict[tuple[str, str], LeaseRecord] = field(default_factory=dict)
    _tick: int = 0

    def advance(self) -> int:
        self._tick += 1
        return self._tick

    def get(self, buyer_id: str, model_id: str) -> LeaseRecord | None:
        key = (buyer_id, model_id)
        lease = self._leases.get(key)
        if lease is None:
            return None
        if lease.expires_at_tick < self._tick:
            self._leases.pop(key, None)
            return None
        return lease

    def refresh(
        self,
        *,
        buyer_id: str,
        model_id: str,
        worker_id: str,
        execution_mode: ExecutionMode,
    ) -> LeaseRecord:
        lease = LeaseRecord(
            buyer_id=buyer_id,
            model_id=model_id,
            worker_id=worker_id,
            execution_mode=execution_mode,
            expires_at_tick=self._tick + self.ttl_ticks,
        )
        self._leases[(buyer_id, model_id)] = lease
        return lease

    def break_for_buyer_model(self, buyer_id: str, model_id: str) -> None:
        self._leases.pop((buyer_id, model_id), None)

    def break_for_worker(self, worker_id: str) -> None:
        expired_keys = [
            key for key, lease in self._leases.items() if lease.worker_id == worker_id
        ]
        for key in expired_keys:
            self._leases.pop(key, None)


@dataclass
class InMemoryRouteTraceStore:
    _traces: dict[str, RouteTraceRecord] = field(default_factory=dict)
    _next_trace_number: int = 1
    _tick: int = 0

    def create(
        self,
        *,
        request: ChatRequest,
        draft: RouteTraceDraft,
        attempt_number: int,
        retry_count: int,
    ) -> RouteTraceRecord:
        self._tick += 1
        trace_id = f"trace-{self._next_trace_number:05d}"
        self._next_trace_number += 1
        decision = draft.decision
        record = RouteTraceRecord(
            trace_id=trace_id,
            model_id=request.model_id,
            buyer_id=request.buyer_id,
            selected_source=request.execution_mode.value,
            resolved_scope=draft.resolved_scope,
            private_network_id=request.private_network_id,
            requested_execution_mode=request.execution_mode,
            attempt_number=attempt_number,
            retry_count=retry_count,
            eligible_worker_ids=draft.eligible_worker_ids,
            filtered_worker_reasons=draft.filtered_worker_reasons,
            selected_worker_id=decision.worker_id if decision is not None else "",
            selected_worker_kind=decision.worker_kind if decision is not None else None,
            route_reason=decision.reason if decision is not None else "",
            route_reason_code=draft.route_reason_code,
            continuity_used=draft.continuity_used,
            warm_path_used=draft.warm_path_used,
            current_status="selected" if decision is not None else "route_failed",
            final_status="" if decision is not None else "route_failed",
            final_error=draft.error_message if decision is None else "",
            created_at_tick=self._tick,
            updated_at_tick=self._tick,
        )
        self._traces[trace_id] = record
        return record

    def attach_job(self, trace_id: str, job_id: str) -> RouteTraceRecord | None:
        trace = self._traces.get(trace_id)
        if trace is None:
            return None
        return self._update(trace_id, job_id=job_id)

    def mark_claimed(self, trace_id: str) -> RouteTraceRecord | None:
        trace = self._traces.get(trace_id)
        if trace is None:
            return None
        return self._update(trace_id, current_status="claimed")

    def mark_completed(self, trace_id: str) -> RouteTraceRecord | None:
        trace = self._traces.get(trace_id)
        if trace is None:
            return None
        return self._update(trace_id, current_status="completed", final_status="completed")

    def mark_failed(self, trace_id: str, final_error: str) -> RouteTraceRecord | None:
        trace = self._traces.get(trace_id)
        if trace is None:
            return None
        return self._update(
            trace_id,
            current_status="failed",
            final_status="failed",
            final_error=final_error,
        )

    def mark_retried(self, trace_id: str, final_error: str) -> RouteTraceRecord | None:
        trace = self._traces.get(trace_id)
        if trace is None:
            return None
        return self._update(
            trace_id,
            current_status="retried",
            final_status="retried",
            final_error=final_error,
        )

    def get(self, trace_id: str) -> RouteTraceRecord | None:
        return self._traces.get(trace_id)

    def list_traces(self) -> list[RouteTraceRecord]:
        return list(self._traces.values())

    def _update(self, trace_id: str, **changes) -> RouteTraceRecord:
        self._tick += 1
        updated = replace(self._traces[trace_id], updated_at_tick=self._tick, **changes)
        self._traces[trace_id] = updated
        return updated


@dataclass
class InMemoryModuloService:
    router: TrustRouter
    registry: InMemoryWorkerRegistry = field(default_factory=InMemoryWorkerRegistry)
    jobs: InMemoryJobQueue = field(default_factory=InMemoryJobQueue)
    leases: InMemoryLeaseManager = field(default_factory=InMemoryLeaseManager)
    traces: InMemoryRouteTraceStore = field(default_factory=InMemoryRouteTraceStore)

    def register_worker(self, worker: WorkerSnapshot) -> None:
        self.registry.register(worker)

    def unregister_worker(self, worker_id: str) -> WorkerSnapshot | None:
        self.leases.break_for_worker(worker_id)
        return self.registry.unregister(worker_id)

    def heartbeat_worker(self, heartbeat: WorkerHeartbeat) -> WorkerSnapshot | None:
        return self.registry.heartbeat(heartbeat)

    def route_chat(self, request: ChatRequest) -> RouteDecision:
        self.leases.advance()
        decision, _ = self._route_with_trace(request=request, attempt_number=1, retry_count=0)
        return decision

    def reroute_chat(
        self,
        request: ChatRequest,
        *,
        exclude_worker_ids: set[str],
        attempt_number: int,
        retry_count: int,
    ) -> tuple[RouteDecision, RouteTraceRecord]:
        return self._route_with_trace(
            request=request,
            exclude_worker_ids=exclude_worker_ids,
            attempt_number=attempt_number,
            retry_count=retry_count,
        )

    def submit_chat(self, request: ChatRequest) -> JobRecord:
        route, trace = self._route_with_trace(request=request, attempt_number=1, retry_count=0)
        self._refresh_lease(request, route)
        job = self.jobs.create_job(request=request, route=route, trace_id=trace.trace_id)
        self.traces.attach_job(trace.trace_id, job.job_id)
        return job

    def claim_job(self, worker_id: str) -> JobClaim | None:
        claim = self.jobs.claim_for_worker(worker_id)
        if claim is not None and claim.trace_id:
            self.traces.mark_claimed(claim.trace_id)
        return claim

    def complete_job(self, result: JobResult) -> JobRecord:
        completed = self.jobs.complete(result)
        if completed.trace_id:
            self.traces.mark_completed(completed.trace_id)
        self._refresh_lease(completed.request, completed.route)
        return completed

    def fail_job(self, failure: JobFailure) -> JobRecord:
        reason = f"{failure.error_code}: {failure.message}"
        self.registry.mark_unhealthy(failure.worker_id, reason)
        self.leases.break_for_worker(failure.worker_id)

        job = self.get_job(failure.job_id)
        if job is None:
            raise JobQueueError(f"Unknown job id: {failure.job_id}")

        should_retry = job.attempts < 2
        if should_retry:
            try:
                if job.trace_id:
                    self.traces.mark_retried(job.trace_id, reason)
                route, trace = self.reroute_chat(
                    job.request,
                    exclude_worker_ids={failure.worker_id},
                    attempt_number=job.attempts + 1,
                    retry_count=job.attempts,
                )
            except RoutingError:
                if job.trace_id:
                    self.traces.mark_failed(job.trace_id, reason)
                return self.jobs.fail(failure)
            self._refresh_lease(job.request, route)
            return self.jobs.retry(
                job_id=failure.job_id,
                route=route,
                failure_reason=reason,
                trace_id=trace.trace_id,
            )

        if job.trace_id:
            self.traces.mark_failed(job.trace_id, reason)
        return self.jobs.fail(failure)

    def timeout_job(self, job_id: str, worker_id: str) -> JobRecord:
        return self.fail_job(
            JobFailure(
                job_id=job_id,
                worker_id=worker_id,
                error_code="EXEC_TIMEOUT",
                message="Execution timed out",
            )
        )

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)

    def health_summary(self) -> dict[str, int]:
        return self.registry.health_summary()

    def smoke_test(self, request: ChatRequest) -> tuple[bool, str]:
        try:
            decision, _ = self._route_with_trace(request=request, attempt_number=1, retry_count=0)
        except RoutingError as exc:
            return False, str(exc)
        return True, decision.reason

    def get_trace(self, trace_id: str) -> RouteTraceRecord | None:
        return self.traces.get(trace_id)

    def list_traces(self) -> list[RouteTraceRecord]:
        return self.traces.list_traces()

    def _route_via_lease(self, request: ChatRequest) -> RouteDecision | None:
        if not request.buyer_id:
            return None
        lease = self.leases.get(request.buyer_id, request.model_id)
        if lease is None:
            return None
        if request.execution_mode is not lease.execution_mode:
            return None
        worker = self.registry.get(lease.worker_id)
        if worker is None:
            self.leases.break_for_buyer_model(request.buyer_id, request.model_id)
            return None
        expected_kind = {
            ExecutionMode.LOCAL: "local",
            ExecutionMode.NETWORK: "network",
            ExecutionMode.CLOUD: "cloud",
        }[lease.execution_mode]
        if worker.kind.value != expected_kind:
            self.leases.break_for_buyer_model(request.buyer_id, request.model_id)
            return None
        if worker.resolved_scope() is not request.resolved_scope():
            self.leases.break_for_buyer_model(request.buyer_id, request.model_id)
            return None
        if (
            request.resolved_scope() is RouteScope.PRIVATE
            and request.private_network_id
            and worker.private_network_id != request.private_network_id
        ):
            self.leases.break_for_buyer_model(request.buyer_id, request.model_id)
            return None
        model_state = worker.supports_model(request.model_id)
        if (
            not worker.healthy
            or model_state is None
            or model_state.current_load >= worker.max_concurrency
        ):
            self.leases.break_for_buyer_model(request.buyer_id, request.model_id)
            return None

        self.leases.refresh(
            buyer_id=request.buyer_id,
            model_id=request.model_id,
            worker_id=worker.worker_id,
            execution_mode=lease.execution_mode,
        )
        return RouteDecision(
            worker_id=worker.worker_id,
            worker_kind=worker.kind,
            model_id=request.model_id,
            execution_mode=lease.execution_mode,
            reason="Selected active leased worker for buyer continuity.",
        )

    def _route_with_trace(
        self,
        *,
        request: ChatRequest,
        exclude_worker_ids: set[str] | None = None,
        attempt_number: int,
        retry_count: int,
    ) -> tuple[RouteDecision, RouteTraceRecord]:
        lease_decision = self._route_via_lease(request)
        if lease_decision is not None:
            draft = RouteTraceDraft(
                decision=lease_decision,
                resolved_scope=request.resolved_scope(),
                eligible_worker_ids=(lease_decision.worker_id,),
                filtered_worker_reasons=(),
                route_reason_code="buyer_continuity_lease",
                continuity_used=True,
            )
        else:
            draft = self.router.trace_route(
                request=request,
                workers=self.registry.list_workers(),
                exclude_worker_ids=exclude_worker_ids,
            )

        trace = self.traces.create(
            request=request,
            draft=draft,
            attempt_number=attempt_number,
            retry_count=retry_count,
        )
        if draft.decision is None:
            raise RoutingError(draft.error_message or "No eligible execution target found.")
        return draft.decision, trace

    def _refresh_lease(self, request: ChatRequest, route: RouteDecision) -> None:
        if not request.buyer_id:
            return
        self.leases.refresh(
            buyer_id=request.buyer_id,
            model_id=request.model_id,
            worker_id=route.worker_id,
            execution_mode=route.execution_mode,
        )


@dataclass(frozen=True)
class InMemoryWorkerControlPlane:
    service: InMemoryModuloService

    def register_worker(self, worker: WorkerSnapshot) -> None:
        self.service.register_worker(worker)

    def heartbeat_worker(self, heartbeat: WorkerHeartbeat) -> WorkerSnapshot | None:
        return self.service.heartbeat_worker(heartbeat)

    def claim_job(self, worker_id: str) -> JobClaim | None:
        return self.service.claim_job(worker_id)

    def complete_job(self, result: JobResult) -> JobRecord:
        return self.service.complete_job(result)

    def fail_job(self, failure: JobFailure) -> JobRecord:
        return self.service.fail_job(failure)
