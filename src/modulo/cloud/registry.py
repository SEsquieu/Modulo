from __future__ import annotations

from dataclasses import dataclass, field

from modulo.common.contracts import WorkerHeartbeat, WorkerModelState, WorkerSnapshot


@dataclass
class InMemoryWorkerRegistry:
    _workers: dict[str, WorkerSnapshot] = field(default_factory=dict)

    def register(self, worker: WorkerSnapshot) -> None:
        self._workers[worker.worker_id] = worker

    def get(self, worker_id: str) -> WorkerSnapshot | None:
        return self._workers.get(worker_id)

    def list_workers(self) -> list[WorkerSnapshot]:
        return list(self._workers.values())

    def unregister(self, worker_id: str) -> WorkerSnapshot | None:
        return self._workers.pop(worker_id, None)

    def heartbeat(self, heartbeat: WorkerHeartbeat) -> WorkerSnapshot | None:
        worker = self._workers.get(heartbeat.worker_id)
        if worker is None:
            return None

        advertised_models = tuple(
            WorkerModelState(
                model_id=state.model_id,
                runtime_identity=state.runtime_identity,
                current_load=heartbeat.current_load,
                recent_success_rate=state.recent_success_rate,
                timeout_rate=state.timeout_rate,
                confidence=state.confidence,
            )
            for state in worker.advertised_models
        )
        updated = WorkerSnapshot(
            worker_id=worker.worker_id,
            kind=worker.kind,
            healthy=heartbeat.healthy,
            max_concurrency=worker.max_concurrency,
            advertised_models=advertised_models,
            serving_scope=worker.serving_scope,
            private_network_id=worker.private_network_id,
            trust_notes=worker.trust_notes,
        )
        self._workers[worker.worker_id] = updated
        return updated

    def mark_unhealthy(self, worker_id: str, reason: str = "") -> WorkerSnapshot | None:
        worker = self._workers.get(worker_id)
        if worker is None:
            return None

        trust_notes = worker.trust_notes
        if reason:
            trust_notes = (*worker.trust_notes, reason)

        updated = WorkerSnapshot(
            worker_id=worker.worker_id,
            kind=worker.kind,
            healthy=False,
            max_concurrency=worker.max_concurrency,
            advertised_models=worker.advertised_models,
            serving_scope=worker.serving_scope,
            private_network_id=worker.private_network_id,
            trust_notes=trust_notes,
        )
        self._workers[worker.worker_id] = updated
        return updated

    def health_summary(self) -> dict[str, int]:
        healthy = sum(1 for worker in self._workers.values() if worker.healthy)
        unhealthy = len(self._workers) - healthy
        return {
            "total_workers": len(self._workers),
            "healthy_workers": healthy,
            "unhealthy_workers": unhealthy,
        }
