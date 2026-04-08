from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from typing import Protocol

from modulo.common.contracts import (
    ChatRequest,
    ExecutionMode,
    JobClaim,
    JobFailure,
    JobResult,
    WorkerBridgeConfig,
    WorkerHeartbeat,
)


class WorkerTransportError(Exception):
    """Raised when the worker transport cannot complete a control-plane action."""


class WorkerTransportApp(Protocol):
    def handle(self, method: str, path: str, body: bytes | None = None) -> tuple[int, dict]:
        """Handle an HTTP-shaped request for worker transport calls."""


@dataclass(frozen=True)
class InProcessWorkerHTTPTransport:
    app: WorkerTransportApp
    config: WorkerBridgeConfig

    def register_worker(self) -> None:
        status, payload = self.app.handle(
            "POST",
            "/worker/register",
            self._encode_json(
                {
                    "worker_id": self.config.worker_id,
                    "kind": self.config.kind.value,
                    "max_concurrency": self.config.max_concurrency,
                    "models": list(self.config.enabled_models),
                }
            ),
        )
        self._require_ok(status, payload, "register worker")

    def heartbeat_worker(self, heartbeat: WorkerHeartbeat) -> None:
        status, payload = self.app.handle(
            "POST",
            "/worker/heartbeat",
            self._encode_json(
                {
                    "worker_id": heartbeat.worker_id,
                    "healthy": heartbeat.healthy,
                    "current_load": heartbeat.current_load,
                }
            ),
        )
        self._require_ok(status, payload, "heartbeat worker")

    def claim_job(self, worker_id: str) -> JobClaim | None:
        status, payload = self.app.handle(
            "POST",
            "/worker/jobs/claim",
            self._encode_json({"worker_id": worker_id}),
        )
        self._require_ok(status, payload, "claim job")

        job_payload = payload.get("job")
        if job_payload is None:
            return None

        model_id = job_payload.get("model")
        stream = bool(job_payload.get("stream", False))
        if not isinstance(model_id, str):
            raise WorkerTransportError("Claim response missing job model")

        return JobClaim(
            job_id=job_payload["job_id"],
            worker_id=worker_id,
            request=ChatRequest(
                model_id=model_id,
                execution_mode=ExecutionMode.NETWORK,
                stream=stream,
            ),
            route=self._route_from_payload(job_payload.get("route", {}), model_id),
        )

    def complete_job(self, result: JobResult) -> None:
        status, payload = self.app.handle(
            "POST",
            f"/worker/jobs/{result.job_id}/result",
            self._encode_json(
                {
                    "worker_id": result.worker_id,
                    "response_text": result.response_text,
                }
            ),
        )
        self._require_ok(status, payload, "complete job")

    def fail_job(self, failure: JobFailure) -> None:
        status, payload = self.app.handle(
            "POST",
            f"/worker/jobs/{failure.job_id}/fail",
            self._encode_json(
                {
                    "worker_id": failure.worker_id,
                    "error_code": failure.error_code,
                    "message": failure.message,
                }
            ),
        )
        self._require_ok(status, payload, "fail job")

    @staticmethod
    def _encode_json(payload: dict) -> bytes:
        return json.dumps(payload).encode("utf-8")

    @staticmethod
    def _require_ok(status: int, payload: dict, action: str) -> None:
        if status != HTTPStatus.OK:
            error_message = payload.get("error", "unknown error")
            raise WorkerTransportError(f"Failed to {action}: {error_message}")

    @staticmethod
    def _route_from_payload(payload: dict, model_id: str):
        from modulo.common.contracts import ExecutionMode, RouteDecision, WorkerKind

        worker_id = payload.get("worker_id")
        worker_kind = payload.get("worker_kind")
        routed_via_fallback = bool(payload.get("routed_via_fallback", False))
        if not isinstance(worker_id, str) or not isinstance(worker_kind, str):
            raise WorkerTransportError("Claim response missing route metadata")

        return RouteDecision(
            worker_id=worker_id,
            worker_kind=WorkerKind(worker_kind),
            model_id=model_id,
            execution_mode=ExecutionMode.NETWORK,
            routed_via_fallback=routed_via_fallback,
            reason="Claimed via worker transport",
        )
