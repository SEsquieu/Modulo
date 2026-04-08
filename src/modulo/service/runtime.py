from __future__ import annotations

from dataclasses import dataclass, field

from modulo.common.contracts import ChatRequest, RouteDecision, WorkerSnapshot
from modulo.service.router import RoutingError, TrustRouter


@dataclass
class InMemoryModuloService:
    router: TrustRouter
    workers: list[WorkerSnapshot] = field(default_factory=list)

    def register_worker(self, worker: WorkerSnapshot) -> None:
        self.workers = [existing for existing in self.workers if existing.worker_id != worker.worker_id]
        self.workers.append(worker)

    def route_chat(self, request: ChatRequest) -> RouteDecision:
        return self.router.route(request=request, workers=self.workers)

    def health_summary(self) -> dict[str, int]:
        healthy = sum(1 for worker in self.workers if worker.healthy)
        unhealthy = len(self.workers) - healthy
        return {
            "total_workers": len(self.workers),
            "healthy_workers": healthy,
            "unhealthy_workers": unhealthy,
        }

    def smoke_test(self, request: ChatRequest) -> tuple[bool, str]:
        try:
            decision = self.route_chat(request)
        except RoutingError as exc:
            return False, str(exc)
        return True, decision.reason

