from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol

from modulo.common.contracts import (
    ChatRequest,
    JobFailure,
    JobResult,
    JobStatus,
    WorkerBridgeConfig,
    WorkerHeartbeat,
    WorkerRuntimeState,
    WorkerStatusSnapshot,
)
from modulo.worker.errors import WorkerExecutionError
from modulo.worker.executors import StubExecutor
from modulo.worker.transport import WorkerTransportError


class WorkerExecutor(Protocol):
    def execute(self, worker_id: str, request: ChatRequest) -> str:
        """Execute a claimed job for a worker."""


class WorkerTransport(Protocol):
    def register_worker(self) -> None:
        """Register the worker with the control plane."""

    def heartbeat_worker(self, heartbeat: WorkerHeartbeat) -> None:
        """Update worker liveness and load information."""

    def claim_job(self, worker_id: str):
        """Claim the next eligible job for the worker."""

    def complete_job(self, result: JobResult) -> None:
        """Record a successful job result."""

    def fail_job(self, failure: JobFailure) -> None:
        """Record a failed job result."""


class InMemoryWorkerRuntime(StubExecutor):
    """Backwards-compatible name for the deterministic stub executor."""


@dataclass
class WorkerBridgeRuntime:
    config: WorkerBridgeConfig
    transport: WorkerTransport
    executor: WorkerExecutor
    _status: WorkerStatusSnapshot = field(init=False)

    def __post_init__(self) -> None:
        self._status = WorkerStatusSnapshot(
            worker_id=self.config.worker_id,
            enabled_models=self.config.enabled_models,
        )

    def get_status(self) -> WorkerStatusSnapshot:
        return self._status

    def start(self) -> WorkerStatusSnapshot:
        self._status = replace(
            self._status,
            desired_running=True,
            runtime_state=WorkerRuntimeState.STARTING,
            healthy=True,
            last_error="",
        )
        try:
            self.transport.register_worker()
            self.transport.heartbeat_worker(
                WorkerHeartbeat(
                    worker_id=self.config.worker_id,
                    healthy=True,
                    current_load=0,
                )
            )
        except WorkerTransportError as exc:
            self._status = replace(
                self._status,
                desired_running=False,
                runtime_state=WorkerRuntimeState.ERROR,
                healthy=False,
                registered_with_cloud=False,
                last_error=str(exc),
            )
            return self._status

        self._status = replace(
            self._status,
            runtime_state=WorkerRuntimeState.IDLE,
            registered_with_cloud=True,
            healthy=True,
            current_load=0,
        )
        return self._status

    def stop(self) -> WorkerStatusSnapshot:
        if self._status.registered_with_cloud:
            try:
                self.transport.heartbeat_worker(
                    WorkerHeartbeat(
                        worker_id=self.config.worker_id,
                        healthy=False,
                        current_load=0,
                    )
                )
            except WorkerTransportError as exc:
                self._status = replace(
                    self._status,
                    runtime_state=WorkerRuntimeState.ERROR,
                    last_error=str(exc),
                )
                return self._status
        self._status = replace(
            self._status,
            desired_running=False,
            runtime_state=WorkerRuntimeState.STOPPED,
            registered_with_cloud=False,
            healthy=False,
            current_load=0,
        )
        return self._status

    def restart(self) -> WorkerStatusSnapshot:
        self.stop()
        return self.start()

    def run_cycle(self) -> WorkerStatusSnapshot:
        if not self._status.desired_running:
            return self._status

        if not self._status.registered_with_cloud:
            return self.start()

        try:
            self.transport.heartbeat_worker(
                WorkerHeartbeat(
                    worker_id=self.config.worker_id,
                    healthy=True,
                    current_load=0,
                )
            )
            claim = self.transport.claim_job(self.config.worker_id)
        except WorkerTransportError as exc:
            self._status = replace(
                self._status,
                runtime_state=WorkerRuntimeState.ERROR,
                healthy=False,
                current_load=0,
                last_error=str(exc),
            )
            return self._status

        if claim is None:
            self._status = replace(
                self._status,
                runtime_state=WorkerRuntimeState.IDLE,
                healthy=True,
                current_load=0,
            )
            return self._status

        self._status = replace(
            self._status,
            runtime_state=WorkerRuntimeState.BUSY,
            healthy=True,
            current_load=1,
            last_job_id=claim.job_id,
            last_job_status=JobStatus.CLAIMED,
        )
        try:
            self.transport.heartbeat_worker(
                WorkerHeartbeat(
                    worker_id=self.config.worker_id,
                    healthy=True,
                    current_load=1,
                )
            )
        except WorkerTransportError as exc:
            self._status = replace(
                self._status,
                runtime_state=WorkerRuntimeState.ERROR,
                healthy=False,
                current_load=0,
                last_error=str(exc),
            )
            return self._status

        try:
            response_text = self.executor.execute(self.config.worker_id, claim.request)
            self.transport.complete_job(
                JobResult(
                    job_id=claim.job_id,
                    worker_id=self.config.worker_id,
                    response_text=response_text,
                )
            )
        except WorkerExecutionError as exc:
            return self._handle_execution_failure(claim.job_id, str(exc))
        except WorkerTransportError as exc:
            self._status = replace(
                self._status,
                runtime_state=WorkerRuntimeState.ERROR,
                healthy=False,
                current_load=0,
                last_error=str(exc),
            )
            return self._status

        try:
            self.transport.heartbeat_worker(
                WorkerHeartbeat(
                    worker_id=self.config.worker_id,
                    healthy=True,
                    current_load=0,
                )
            )
        except WorkerTransportError as exc:
            self._status = replace(
                self._status,
                runtime_state=WorkerRuntimeState.ERROR,
                healthy=False,
                current_load=0,
                last_job_status=JobStatus.COMPLETED,
                last_error=str(exc),
                completed_jobs=self._status.completed_jobs + 1,
            )
            return self._status

        self._status = replace(
            self._status,
            runtime_state=WorkerRuntimeState.IDLE,
            healthy=True,
            current_load=0,
            last_job_status=JobStatus.COMPLETED,
            last_error="",
            completed_jobs=self._status.completed_jobs + 1,
        )
        return self._status

    def _handle_execution_failure(self, job_id: str, message: str) -> WorkerStatusSnapshot:
        try:
            self.transport.fail_job(
                JobFailure(
                    job_id=job_id,
                    worker_id=self.config.worker_id,
                    error_code="EXEC_ERROR",
                    message=message,
                )
            )
            self.transport.heartbeat_worker(
                WorkerHeartbeat(
                    worker_id=self.config.worker_id,
                    healthy=True,
                    current_load=0,
                )
            )
        except WorkerTransportError as exc:
            self._status = replace(
                self._status,
                runtime_state=WorkerRuntimeState.ERROR,
                healthy=False,
                current_load=0,
                last_job_status=JobStatus.FAILED,
                last_error=str(exc),
                failed_jobs=self._status.failed_jobs + 1,
            )
            return self._status

        self._status = replace(
            self._status,
            runtime_state=WorkerRuntimeState.ERROR,
            healthy=True,
            current_load=0,
            last_job_status=JobStatus.FAILED,
            last_error=message,
            failed_jobs=self._status.failed_jobs + 1,
        )
        return self._status
