from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol

from modulo.common.contracts import (
    ChatRequest,
    JobClaim,
    JobFailure,
    JobResult,
    JobStatus,
    WorkerBridgeConfig,
    WorkerHeartbeat,
    WorkerModelState,
    WorkerRuntimeState,
    WorkerSnapshot,
    WorkerStatusSnapshot,
)


class WorkerExecutionError(Exception):
    """Raised when an in-memory worker runtime cannot execute a job."""


class WorkerExecutor(Protocol):
    def execute(self, worker_id: str, request: ChatRequest) -> str:
        """Execute a claimed job for a worker."""


class WorkerControlPlane(Protocol):
    def register_worker(self, worker: WorkerSnapshot) -> None:
        """Register the worker with the control plane."""

    def heartbeat_worker(self, heartbeat: WorkerHeartbeat) -> WorkerSnapshot | None:
        """Update worker liveness and load information."""

    def claim_job(self, worker_id: str) -> JobClaim | None:
        """Claim the next eligible job for the worker."""

    def complete_job(self, result: JobResult):
        """Record a successful job result."""

    def fail_job(self, failure: JobFailure):
        """Record a failed job result."""


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


@dataclass
class WorkerBridgeRuntime:
    config: WorkerBridgeConfig
    control_plane: WorkerControlPlane
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
        self.control_plane.register_worker(self._build_worker_snapshot(healthy=True, current_load=0))
        self.control_plane.heartbeat_worker(
            WorkerHeartbeat(
                worker_id=self.config.worker_id,
                healthy=True,
                current_load=0,
            )
        )
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
            self.control_plane.heartbeat_worker(
                WorkerHeartbeat(
                    worker_id=self.config.worker_id,
                    healthy=False,
                    current_load=0,
                )
            )
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

        self.control_plane.heartbeat_worker(
            WorkerHeartbeat(
                worker_id=self.config.worker_id,
                healthy=True,
                current_load=0,
            )
        )

        claim = self.control_plane.claim_job(self.config.worker_id)
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
        self.control_plane.heartbeat_worker(
            WorkerHeartbeat(
                worker_id=self.config.worker_id,
                healthy=True,
                current_load=1,
            )
        )

        try:
            response_text = self.executor.execute(self.config.worker_id, claim.request)
            self.control_plane.complete_job(
                JobResult(
                    job_id=claim.job_id,
                    worker_id=self.config.worker_id,
                    response_text=response_text,
                )
            )
        except WorkerExecutionError as exc:
            self.control_plane.fail_job(
                JobFailure(
                    job_id=claim.job_id,
                    worker_id=self.config.worker_id,
                    error_code="EXEC_ERROR",
                    message=str(exc),
                )
            )
            self._status = replace(
                self._status,
                runtime_state=WorkerRuntimeState.ERROR,
                healthy=True,
                current_load=0,
                last_job_status=JobStatus.FAILED,
                last_error=str(exc),
                failed_jobs=self._status.failed_jobs + 1,
            )
            self.control_plane.heartbeat_worker(
                WorkerHeartbeat(
                    worker_id=self.config.worker_id,
                    healthy=True,
                    current_load=0,
                )
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
        self.control_plane.heartbeat_worker(
            WorkerHeartbeat(
                worker_id=self.config.worker_id,
                healthy=True,
                current_load=0,
            )
        )
        return self._status

    def _build_worker_snapshot(self, *, healthy: bool, current_load: int) -> WorkerSnapshot:
        return WorkerSnapshot(
            worker_id=self.config.worker_id,
            kind=self.config.kind,
            healthy=healthy,
            max_concurrency=self.config.max_concurrency,
            advertised_models=tuple(
                WorkerModelState(
                    model_id=model_id,
                    runtime_identity=model_id,
                    current_load=current_load,
                )
                for model_id in self.config.enabled_models
            ),
        )
