from __future__ import annotations

from dataclasses import dataclass, field

from modulo.common.contracts import ChatRequest


class WorkerExecutionError(Exception):
    """Raised when an in-memory worker runtime cannot execute a job."""


@dataclass
class InMemoryWorkerRuntime:
    _responses: dict[str, str] = field(default_factory=dict)

    def register_worker(self, worker_id: str, response_text: str) -> None:
        self._responses[worker_id] = response_text

    def execute(self, worker_id: str, request: ChatRequest) -> str:
        del request
        response = self._responses.get(worker_id)
        if response is None:
            raise WorkerExecutionError(f"No execution adapter registered for {worker_id}")
        return response
