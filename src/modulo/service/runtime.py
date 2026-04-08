from __future__ import annotations

from dataclasses import dataclass, field

from modulo.common.contracts import (
    ChatRequest,
    JobClaim,
    JobFailure,
    JobRecord,
    JobResult,
    RouteDecision,
    WorkerHeartbeat,
    WorkerSnapshot,
)
from modulo.service.jobs import InMemoryJobQueue
from modulo.service.registry import InMemoryWorkerRegistry
from modulo.service.router import RoutingError, TrustRouter


@dataclass
class InMemoryModuloService:
    router: TrustRouter
    registry: InMemoryWorkerRegistry = field(default_factory=InMemoryWorkerRegistry)
    jobs: InMemoryJobQueue = field(default_factory=InMemoryJobQueue)

    def register_worker(self, worker: WorkerSnapshot) -> None:
        self.registry.register(worker)

    def heartbeat_worker(self, heartbeat: WorkerHeartbeat) -> WorkerSnapshot | None:
        return self.registry.heartbeat(heartbeat)

    def route_chat(self, request: ChatRequest) -> RouteDecision:
        return self.router.route(request=request, workers=self.registry.list_workers())

    def submit_chat(self, request: ChatRequest) -> JobRecord:
        route = self.route_chat(request)
        return self.jobs.create_job(request=request, route=route)

    def claim_job(self, worker_id: str) -> JobClaim | None:
        return self.jobs.claim_for_worker(worker_id)

    def complete_job(self, result: JobResult) -> JobRecord:
        return self.jobs.complete(result)

    def fail_job(self, failure: JobFailure) -> JobRecord:
        return self.jobs.fail(failure)

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
