from __future__ import annotations

from dataclasses import dataclass, field

from modulo.common.contracts import (
    ChatRequest,
    ExecutionMode,
    JobClaim,
    JobFailure,
    JobRecord,
    JobResult,
    RouteScope,
    RouteDecision,
    WorkerHeartbeat,
    WorkerSnapshot,
)
from modulo.cloud.jobs import InMemoryJobQueue, JobQueueError
from modulo.cloud.registry import InMemoryWorkerRegistry
from modulo.cloud.router import RoutingError, TrustRouter


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
class InMemoryModuloService:
    router: TrustRouter
    registry: InMemoryWorkerRegistry = field(default_factory=InMemoryWorkerRegistry)
    jobs: InMemoryJobQueue = field(default_factory=InMemoryJobQueue)
    leases: InMemoryLeaseManager = field(default_factory=InMemoryLeaseManager)

    def register_worker(self, worker: WorkerSnapshot) -> None:
        self.registry.register(worker)

    def heartbeat_worker(self, heartbeat: WorkerHeartbeat) -> WorkerSnapshot | None:
        return self.registry.heartbeat(heartbeat)

    def route_chat(self, request: ChatRequest) -> RouteDecision:
        self.leases.advance()
        lease_decision = self._route_via_lease(request)
        if lease_decision is not None:
            return lease_decision
        return self.router.route(request=request, workers=self.registry.list_workers())

    def reroute_chat(
        self,
        request: ChatRequest,
        *,
        exclude_worker_ids: set[str],
    ) -> RouteDecision:
        return self.router.route(
            request=request,
            workers=self.registry.list_workers(),
            exclude_worker_ids=exclude_worker_ids,
        )

    def submit_chat(self, request: ChatRequest) -> JobRecord:
        route = self.route_chat(request)
        self._refresh_lease(request, route)
        return self.jobs.create_job(request=request, route=route)

    def claim_job(self, worker_id: str) -> JobClaim | None:
        return self.jobs.claim_for_worker(worker_id)

    def complete_job(self, result: JobResult) -> JobRecord:
        completed = self.jobs.complete(result)
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
                route = self.reroute_chat(
                    job.request,
                    exclude_worker_ids={failure.worker_id},
                )
            except RoutingError:
                return self.jobs.fail(failure)
            self._refresh_lease(job.request, route)
            return self.jobs.retry(
                job_id=failure.job_id,
                route=route,
                failure_reason=reason,
            )

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
            decision = self.route_chat(request)
        except RoutingError as exc:
            return False, str(exc)
        return True, decision.reason

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
