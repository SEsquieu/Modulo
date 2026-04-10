from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from typing import Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request

from modulo.common.contracts import (
    ChatMessage,
    ChatRequest,
    ExecutionMode,
    JobClaim,
    JobFailure,
    JobResult,
    RouteScope,
    WorkerBridgeConfig,
    WorkerHeartbeat,
)


class WorkerTransportError(Exception):
    """Raised when the worker transport cannot complete a control-plane action."""


class WorkerTransportApp(Protocol):
    def handle(self, method: str, path: str, body: bytes | None = None) -> tuple[int, dict]:
        """Handle an HTTP-shaped request for worker transport calls."""


def _encode_json(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _decode_json_bytes(body: bytes) -> dict:
    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError as exc:
        raise WorkerTransportError("Transport response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise WorkerTransportError("Transport response must be a JSON object")
    return payload


def _decode_json_bytes_safe(body: bytes) -> dict:
    try:
        return _decode_json_bytes(body)
    except WorkerTransportError:
        return {"error": "unknown error"}


def _require_ok(status: int, payload: dict, action: str) -> None:
    if status != HTTPStatus.OK:
        error_message = payload.get("error", "unknown error")
        raise WorkerTransportError(f"Failed to {action}: {error_message}")


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


def _claim_from_payload(job_payload: dict, worker_id: str) -> JobClaim:
    model_id = job_payload.get("model")
    raw_messages = job_payload.get("messages", [])
    stream = bool(job_payload.get("stream", False))
    scope_name = job_payload.get("scope")
    private_network_id = job_payload.get("private_network_id", "")
    trace_id = job_payload.get("trace_id", "")
    if not isinstance(model_id, str):
        raise WorkerTransportError("Claim response missing job model")
    if not isinstance(raw_messages, list):
        raise WorkerTransportError("Claim response missing job messages")
    if scope_name is not None and not isinstance(scope_name, str):
        raise WorkerTransportError("Claim response contains invalid scope")
    if not isinstance(private_network_id, str):
        raise WorkerTransportError("Claim response contains invalid private network id")
    if not isinstance(trace_id, str):
        raise WorkerTransportError("Claim response contains invalid trace id")

    messages: list[ChatMessage] = []
    for item in raw_messages:
        if not isinstance(item, dict):
            raise WorkerTransportError("Claim response contains invalid job messages")
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            raise WorkerTransportError("Claim response contains invalid job messages")
        messages.append(ChatMessage(role=role, content=content))

    requested_scope = None
    if isinstance(scope_name, str):
        try:
            requested_scope = RouteScope(scope_name)
        except ValueError as exc:
            raise WorkerTransportError("Claim response contains unsupported scope") from exc

    job_id = job_payload.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise WorkerTransportError("Claim response missing job id")

    return JobClaim(
        job_id=job_id,
        worker_id=worker_id,
        request=ChatRequest(
            model_id=model_id,
            execution_mode=ExecutionMode.NETWORK,
            messages=tuple(messages),
            stream=stream,
            requested_scope=requested_scope,
            private_network_id=private_network_id,
        ),
        route=_route_from_payload(job_payload.get("route", {}), model_id),
        trace_id=trace_id,
    )


@dataclass(frozen=True)
class InProcessWorkerHTTPTransport:
    app: WorkerTransportApp
    config: WorkerBridgeConfig

    def register_worker(self) -> None:
        status, payload = self.app.handle(
            "POST",
            "/worker/register",
            _encode_json(
                {
                    "worker_id": self.config.worker_id,
                    "kind": self.config.kind.value,
                    "serving_scope": (
                        self.config.serving_scope.value
                        if self.config.serving_scope is not None
                        else None
                    ),
                    "private_network_id": self.config.private_network_id,
                    "max_concurrency": self.config.max_concurrency,
                    "models": list(self.config.enabled_models),
                }
            ),
        )
        _require_ok(status, payload, "register worker")

    def heartbeat_worker(self, heartbeat: WorkerHeartbeat) -> None:
        status, payload = self.app.handle(
            "POST",
            "/worker/heartbeat",
            _encode_json(
                {
                    "worker_id": heartbeat.worker_id,
                    "healthy": heartbeat.healthy,
                    "current_load": heartbeat.current_load,
                }
            ),
        )
        _require_ok(status, payload, "heartbeat worker")

    def claim_job(self, worker_id: str) -> JobClaim | None:
        status, payload = self.app.handle(
            "POST",
            "/worker/jobs/claim",
            _encode_json({"worker_id": worker_id}),
        )
        _require_ok(status, payload, "claim job")

        job_payload = payload.get("job")
        if job_payload is None:
            return None
        return _claim_from_payload(job_payload, worker_id)

    def complete_job(self, result: JobResult) -> None:
        status, payload = self.app.handle(
            "POST",
            f"/worker/jobs/{result.job_id}/result",
            _encode_json(
                {
                    "worker_id": result.worker_id,
                    "response_text": result.response_text,
                }
            ),
        )
        _require_ok(status, payload, "complete job")

    def fail_job(self, failure: JobFailure) -> None:
        status, payload = self.app.handle(
            "POST",
            f"/worker/jobs/{failure.job_id}/fail",
            _encode_json(
                {
                    "worker_id": failure.worker_id,
                    "error_code": failure.error_code,
                    "message": failure.message,
                }
            ),
        )
        _require_ok(status, payload, "fail job")


@dataclass(frozen=True)
class UrllibWorkerHTTPTransport:
    config: WorkerBridgeConfig
    timeout_seconds: float = 10.0

    def register_worker(self) -> None:
        status, payload = self._post(
            "/worker/register",
            {
                "worker_id": self.config.worker_id,
                "kind": self.config.kind.value,
                "serving_scope": (
                    self.config.serving_scope.value if self.config.serving_scope is not None else None
                ),
                "private_network_id": self.config.private_network_id,
                "max_concurrency": self.config.max_concurrency,
                "models": list(self.config.enabled_models),
            },
            action="register worker",
        )
        _require_ok(status, payload, "register worker")

    def heartbeat_worker(self, heartbeat: WorkerHeartbeat) -> None:
        status, payload = self._post(
            "/worker/heartbeat",
            {
                "worker_id": heartbeat.worker_id,
                "healthy": heartbeat.healthy,
                "current_load": heartbeat.current_load,
            },
            action="heartbeat worker",
        )
        _require_ok(status, payload, "heartbeat worker")

    def claim_job(self, worker_id: str) -> JobClaim | None:
        status, payload = self._post(
            "/worker/jobs/claim",
            {"worker_id": worker_id},
            action="claim job",
        )
        _require_ok(status, payload, "claim job")
        job_payload = payload.get("job")
        if job_payload is None:
            return None
        if not isinstance(job_payload, dict):
            raise WorkerTransportError("Claim response contains invalid job payload")
        return _claim_from_payload(job_payload, worker_id)

    def complete_job(self, result: JobResult) -> None:
        status, payload = self._post(
            f"/worker/jobs/{result.job_id}/result",
            {
                "worker_id": result.worker_id,
                "response_text": result.response_text,
            },
            action="complete job",
        )
        _require_ok(status, payload, "complete job")

    def fail_job(self, failure: JobFailure) -> None:
        status, payload = self._post(
            f"/worker/jobs/{failure.job_id}/fail",
            {
                "worker_id": failure.worker_id,
                "error_code": failure.error_code,
                "message": failure.message,
            },
            action="fail job",
        )
        _require_ok(status, payload, "fail job")

    def _post(self, path: str, payload: dict, *, action: str) -> tuple[int, dict]:
        url = f"{self.config.modulo_url.rstrip('/')}{path}"
        req = urllib_request.Request(
            url,
            data=_encode_json(payload),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=self.timeout_seconds) as response:
                return response.getcode(), _decode_json_bytes(response.read())
        except urllib_error.HTTPError as exc:
            return exc.code, _decode_json_bytes_safe(exc.read())
        except (urllib_error.URLError, OSError) as exc:
            raise WorkerTransportError(f"Failed to {action}: request to {url} failed: {exc}") from exc
