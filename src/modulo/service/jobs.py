from __future__ import annotations

from dataclasses import dataclass, field

from modulo.common.contracts import (
    ChatRequest,
    JobClaim,
    JobFailure,
    JobRecord,
    JobResult,
    JobStatus,
    RouteDecision,
)


class JobQueueError(Exception):
    """Raised when a job cannot be claimed or updated."""


@dataclass
class InMemoryJobQueue:
    _jobs: dict[str, JobRecord] = field(default_factory=dict)
    _next_job_number: int = 1

    def create_job(self, request: ChatRequest, route: RouteDecision) -> JobRecord:
        job_id = f"job-{self._next_job_number:05d}"
        self._next_job_number += 1
        record = JobRecord(
            job_id=job_id,
            request=request,
            status=JobStatus.PENDING,
            route=route,
            assigned_worker_id=route.worker_id,
            assigned_worker_kind=route.worker_kind,
        )
        self._jobs[job_id] = record
        return record

    def claim_for_worker(self, worker_id: str) -> JobClaim | None:
        for job in self._jobs.values():
            if job.assigned_worker_id != worker_id or job.status is not JobStatus.PENDING:
                continue

            claimed = JobRecord(
                job_id=job.job_id,
                request=job.request,
                status=JobStatus.CLAIMED,
                route=job.route,
                assigned_worker_id=job.assigned_worker_id,
                assigned_worker_kind=job.assigned_worker_kind,
                attempts=job.attempts,
            )
            self._jobs[job.job_id] = claimed
            return JobClaim(
                job_id=job.job_id,
                worker_id=worker_id,
                request=job.request,
                route=job.route,
            )
        return None

    def complete(self, result: JobResult) -> JobRecord:
        job = self._require_assigned_claimed_job(result.job_id, result.worker_id)
        completed = JobRecord(
            job_id=job.job_id,
            request=job.request,
            status=JobStatus.COMPLETED,
            route=job.route,
            assigned_worker_id=job.assigned_worker_id,
            assigned_worker_kind=job.assigned_worker_kind,
            attempts=job.attempts,
            response_text=result.response_text,
        )
        self._jobs[job.job_id] = completed
        return completed

    def fail(self, failure: JobFailure) -> JobRecord:
        job = self._require_assigned_claimed_job(failure.job_id, failure.worker_id)
        failed = JobRecord(
            job_id=job.job_id,
            request=job.request,
            status=JobStatus.FAILED,
            route=job.route,
            assigned_worker_id=job.assigned_worker_id,
            assigned_worker_kind=job.assigned_worker_kind,
            attempts=job.attempts,
            failure_reason=f"{failure.error_code}: {failure.message}",
        )
        self._jobs[job.job_id] = failed
        return failed

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[JobRecord]:
        return list(self._jobs.values())

    def _require_assigned_claimed_job(self, job_id: str, worker_id: str) -> JobRecord:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobQueueError(f"Unknown job id: {job_id}")
        if job.assigned_worker_id != worker_id:
            raise JobQueueError(f"Worker {worker_id} is not assigned to {job_id}")
        if job.status is not JobStatus.CLAIMED:
            raise JobQueueError(f"Job {job_id} is not in claimed state")
        return job
