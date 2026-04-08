from __future__ import annotations

from dataclasses import dataclass, field

from modulo.common.contracts import WorkerSnapshot


@dataclass
class InMemoryWorkerRegistry:
    _workers: dict[str, WorkerSnapshot] = field(default_factory=dict)

    def register(self, worker: WorkerSnapshot) -> None:
        self._workers[worker.worker_id] = worker

    def get(self, worker_id: str) -> WorkerSnapshot | None:
        return self._workers.get(worker_id)

    def list_workers(self) -> list[WorkerSnapshot]:
        return list(self._workers.values())

    def health_summary(self) -> dict[str, int]:
        healthy = sum(1 for worker in self._workers.values() if worker.healthy)
        unhealthy = len(self._workers) - healthy
        return {
            "total_workers": len(self._workers),
            "healthy_workers": healthy,
            "unhealthy_workers": unhealthy,
        }
