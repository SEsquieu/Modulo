from __future__ import annotations

import json
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from modulo.common.catalog import SUPPORTED_MODELS
from modulo.common.contracts import (
    ChatMessage,
    ChatRequest,
    ExecutionMode,
    JobFailure,
    JobStatus,
    JobResult,
    RouteScope,
    WorkerHeartbeat,
    WorkerKind,
    WorkerModelState,
    WorkerSnapshot,
)
from modulo.cloud.jobs import JobQueueError
from modulo.cloud.router import RoutingError
from modulo.cloud.runtime import InMemoryModuloService
from modulo.worker.errors import WorkerExecutionError
from modulo.worker.runtime import InMemoryWorkerRuntime


@dataclass
class ModuloHTTPApp:
    service: InMemoryModuloService
    runtime: InMemoryWorkerRuntime
    inline_chat_execution: bool = True
    chat_wait_timeout_seconds: float = 10.0
    chat_wait_poll_seconds: float = 0.05

    def handle(self, method: str, path: str, body: bytes | None = None) -> tuple[int, dict[str, Any]]:
        if method == "GET" and path == "/api/tags":
            return HTTPStatus.OK, self._handle_tags()

        if method == "GET" and path == "/api/platform/status":
            return HTTPStatus.OK, self._handle_platform_status()

        if method == "POST" and path == "/api/chat":
            try:
                payload = json.loads((body or b"{}").decode("utf-8"))
            except json.JSONDecodeError:
                return HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"}
            return self._handle_chat(payload)

        if method == "POST" and path == "/worker/register":
            payload = self._decode_json(body)
            if isinstance(payload, tuple):
                return payload
            return self._handle_worker_register(payload)

        if method == "POST" and path == "/worker/heartbeat":
            payload = self._decode_json(body)
            if isinstance(payload, tuple):
                return payload
            return self._handle_worker_heartbeat(payload)

        if method == "POST" and path == "/worker/jobs/claim":
            payload = self._decode_json(body)
            if isinstance(payload, tuple):
                return payload
            return self._handle_worker_claim(payload)

        if method == "POST" and path.endswith("/result"):
            payload = self._decode_json(body)
            if isinstance(payload, tuple):
                return payload
            return self._handle_worker_result(path, payload)

        if method == "POST" and path.endswith("/fail"):
            payload = self._decode_json(body)
            if isinstance(payload, tuple):
                return payload
            return self._handle_worker_fail(path, payload)

        return HTTPStatus.NOT_FOUND, {"error": "Not found"}

    @staticmethod
    def _decode_json(body: bytes | None) -> dict[str, Any] | tuple[int, dict[str, Any]]:
        try:
            payload = json.loads((body or b"{}").decode("utf-8"))
        except json.JSONDecodeError:
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"}
        if not isinstance(payload, dict):
            return HTTPStatus.BAD_REQUEST, {"error": "JSON object payload required"}
        return payload

    def _handle_tags(self) -> dict[str, Any]:
        models_by_id: dict[str, dict[str, Any]] = {
            model.model_id: {
                "name": model.model_id,
                "model": model.model_id,
            }
            for model in SUPPORTED_MODELS.values()
        }
        for worker in self.service.registry.list_workers():
            if not worker.healthy:
                continue
            for advertised_model in worker.advertised_models:
                models_by_id.setdefault(
                    advertised_model.model_id,
                    {
                        "name": advertised_model.model_id,
                        "model": advertised_model.model_id,
                    },
                )
        return {
            "models": list(models_by_id.values())
        }

    def _handle_platform_status(self) -> dict[str, Any]:
        workers = self.service.registry.list_workers()
        healthy_network_workers = [
            worker for worker in workers if worker.healthy and worker.kind.value == "network"
        ]

        network_models: dict[str, dict[str, Any]] = {}
        for worker in healthy_network_workers:
            for advertised_model in worker.advertised_models:
                canonical = SUPPORTED_MODELS.get(advertised_model.model_id)
                display_name = (
                    canonical.display_name if canonical is not None else advertised_model.model_id
                )
                network_models.setdefault(
                    advertised_model.model_id,
                    {
                        "model_id": advertised_model.model_id,
                        "display_name": display_name,
                        "source": "network",
                        "summary": f"Advertised by healthy network worker {worker.worker_id}.",
                    },
                )

        cloud_models = [
            {
                "model_id": model.model_id,
                "display_name": model.display_name,
                "source": "cloud",
                "summary": "Prototype-safe placeholder trusted cloud catalog.",
            }
            for model in SUPPORTED_MODELS.values()
        ]
        network_summary = (
            f"{len(network_models)} network model(s) are currently advertised by healthy workers."
            if network_models
            else "No network models are currently advertised on this platform target."
        )
        health = self.service.health_summary()
        details = (
            f"Healthy workers: {health['healthy_workers']} / {health['total_workers']}. "
            "Cloud catalog is still a prototype-safe placeholder."
        )
        return {
            "connected": True,
            "summary": "Platform session bridge is connected to the shared control plane.",
            "details": details,
            "account_summary": "Prototype account context is local-only and not authenticated yet.",
            "network_models": list(network_models.values()),
            "cloud_models": cloud_models,
            "credits_summary": "Prototype credits are not implemented yet.",
            "buyer_routing_summary": network_summary,
            "buyer_config_summary": (
                "Buyer routing defaults to platform-managed selection in the current prototype."
            ),
        }

    def _handle_chat(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        model_id = payload.get("model")
        buyer_id = payload.get("buyer_id", "")
        scope_name = payload.get("scope")
        private_network_id = payload.get("private_network_id", "")
        raw_messages = payload.get("messages", [])
        if not isinstance(model_id, str) or not model_id:
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: model"}
        if not isinstance(buyer_id, str):
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: buyer_id"}
        if scope_name is not None and not isinstance(scope_name, str):
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: scope"}
        if not isinstance(private_network_id, str):
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: private_network_id"}
        if not isinstance(raw_messages, list):
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: messages"}

        requested_scope = None
        if isinstance(scope_name, str):
            try:
                requested_scope = RouteScope(scope_name)
            except ValueError:
                return HTTPStatus.BAD_REQUEST, {"error": f"Unsupported scope: {scope_name}"}

        messages: list[ChatMessage] = []
        for item in raw_messages:
            if not isinstance(item, dict):
                return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: messages"}
            role = item.get("role")
            content = item.get("content")
            if not isinstance(role, str) or not isinstance(content, str):
                return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: messages"}
            messages.append(ChatMessage(role=role, content=content))

        request = ChatRequest(
            model_id=model_id,
            execution_mode=ExecutionMode.NETWORK,
            buyer_id=buyer_id,
            messages=tuple(messages),
            stream=bool(payload.get("stream", False)),
            requires_tools=bool(payload.get("tools")),
            requested_scope=requested_scope,
            private_network_id=private_network_id,
        )

        try:
            job = self.service.submit_chat(request)
            if self.inline_chat_execution:
                claim = self.service.claim_job(job.assigned_worker_id)
                if claim is None:
                    raise JobQueueError(f"No claimable job for {job.assigned_worker_id}")

                response_text = self.runtime.execute(claim.worker_id, claim.request)
                completed = self.service.complete_job(
                    JobResult(
                        job_id=claim.job_id,
                        worker_id=claim.worker_id,
                        response_text=response_text,
                    )
                )
            else:
                completed = self._wait_for_job(job.job_id)
        except (RoutingError, WorkerExecutionError, JobQueueError) as exc:
            return HTTPStatus.BAD_GATEWAY, {"error": str(exc)}
        except json.JSONDecodeError:
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"}

        return HTTPStatus.OK, {
            "model": completed.request.model_id,
            "message": {
                "role": "assistant",
                "content": completed.response_text,
            },
            "done": True,
        }

    def _wait_for_job(self, job_id: str):
        deadline = time.monotonic() + self.chat_wait_timeout_seconds
        while time.monotonic() < deadline:
            job = self.service.get_job(job_id)
            if job is None:
                raise JobQueueError(f"Unknown job id: {job_id}")
            if job.status is JobStatus.COMPLETED:
                return job
            if job.status is JobStatus.FAILED:
                raise JobQueueError(job.failure_reason or f"Job {job_id} failed")
            time.sleep(self.chat_wait_poll_seconds)
        raise JobQueueError(f"Timed out waiting for job {job_id} to complete")

    def _handle_worker_register(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        worker_id = payload.get("worker_id")
        kind_name = payload.get("kind", "network")
        scope_name = payload.get("serving_scope")
        private_network_id = payload.get("private_network_id", "")
        max_concurrency = payload.get("max_concurrency", 1)
        model_ids = payload.get("models", [])

        if not isinstance(worker_id, str) or not worker_id:
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: worker_id"}
        if not isinstance(kind_name, str):
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: kind"}
        if scope_name is not None and not isinstance(scope_name, str):
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: serving_scope"}
        if not isinstance(private_network_id, str):
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: private_network_id"}
        if not isinstance(max_concurrency, int) or max_concurrency < 1:
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: max_concurrency"}
        if not isinstance(model_ids, list) or not all(isinstance(model_id, str) for model_id in model_ids):
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: models"}

        try:
            kind = WorkerKind(kind_name)
        except ValueError:
            return HTTPStatus.BAD_REQUEST, {"error": f"Unsupported worker kind: {kind_name}"}
        try:
            serving_scope = RouteScope(scope_name) if scope_name is not None else None
        except ValueError:
            return HTTPStatus.BAD_REQUEST, {"error": f"Unsupported worker scope: {scope_name}"}

        worker = WorkerSnapshot(
            worker_id=worker_id,
            kind=kind,
            healthy=True,
            max_concurrency=max_concurrency,
            advertised_models=tuple(
                WorkerModelState(model_id=model_id, runtime_identity=model_id)
                for model_id in model_ids
            ),
            serving_scope=serving_scope,
            private_network_id=private_network_id,
        )
        self.service.register_worker(worker)
        return HTTPStatus.OK, {
            "worker_id": worker.worker_id,
            "status": "registered",
            "models": [state.model_id for state in worker.advertised_models],
            "serving_scope": worker.resolved_scope().value,
            "private_network_id": worker.private_network_id,
        }

    def _handle_worker_heartbeat(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        worker_id = payload.get("worker_id")
        healthy = payload.get("healthy")
        current_load = payload.get("current_load", 0)

        if not isinstance(worker_id, str) or not worker_id:
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: worker_id"}
        if not isinstance(healthy, bool):
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: healthy"}
        if not isinstance(current_load, int) or current_load < 0:
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid field: current_load"}

        worker = self.service.heartbeat_worker(
            WorkerHeartbeat(worker_id=worker_id, healthy=healthy, current_load=current_load)
        )
        if worker is None:
            return HTTPStatus.NOT_FOUND, {"error": f"Unknown worker: {worker_id}"}

        return HTTPStatus.OK, {
            "worker_id": worker.worker_id,
            "healthy": worker.healthy,
            "current_load": current_load,
        }

    def _handle_worker_claim(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        worker_id = payload.get("worker_id")
        if not isinstance(worker_id, str) or not worker_id:
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: worker_id"}

        claim = self.service.claim_job(worker_id)
        if claim is None:
            return HTTPStatus.OK, {"job": None}

        return HTTPStatus.OK, {
            "job": {
                "job_id": claim.job_id,
                "trace_id": claim.trace_id,
                "model": claim.request.model_id,
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in claim.request.messages
                ],
                "stream": claim.request.stream,
                "scope": claim.request.resolved_scope().value,
                "private_network_id": claim.request.private_network_id,
                "route": {
                    "worker_id": claim.route.worker_id,
                    "worker_kind": claim.route.worker_kind.value,
                    "routed_via_fallback": claim.route.routed_via_fallback,
                },
            }
        }

    def _handle_worker_result(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        job_id = self._job_id_from_path(path, "/result")
        worker_id = payload.get("worker_id")
        response_text = payload.get("response_text")

        if job_id is None:
            return HTTPStatus.NOT_FOUND, {"error": "Invalid job result path"}
        if not isinstance(worker_id, str) or not worker_id:
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: worker_id"}
        if not isinstance(response_text, str):
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: response_text"}

        try:
            completed = self.service.complete_job(
                JobResult(job_id=job_id, worker_id=worker_id, response_text=response_text)
            )
        except JobQueueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

        return HTTPStatus.OK, {"job_id": completed.job_id, "status": completed.status.value}

    def _handle_worker_fail(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        job_id = self._job_id_from_path(path, "/fail")
        worker_id = payload.get("worker_id")
        error_code = payload.get("error_code")
        message = payload.get("message")

        if job_id is None:
            return HTTPStatus.NOT_FOUND, {"error": "Invalid job fail path"}
        if not isinstance(worker_id, str) or not worker_id:
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: worker_id"}
        if not isinstance(error_code, str) or not error_code:
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: error_code"}
        if not isinstance(message, str) or not message:
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: message"}

        try:
            failed = self.service.fail_job(
                JobFailure(
                    job_id=job_id,
                    worker_id=worker_id,
                    error_code=error_code,
                    message=message,
                )
            )
        except JobQueueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

        return HTTPStatus.OK, {"job_id": failed.job_id, "status": failed.status.value}

    @staticmethod
    def _job_id_from_path(path: str, suffix: str) -> str | None:
        prefix = "/worker/jobs/"
        if not path.startswith(prefix) or not path.endswith(suffix):
            return None
        job_id = path[len(prefix) : -len(suffix)]
        return job_id or None


class _ModuloRequestHandler(BaseHTTPRequestHandler):
    app: ModuloHTTPApp

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def log_message(self, format: str, *args: Any) -> None:
        del format, args

    def _dispatch(self, method: str) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else None
        status, payload = self.app.handle(method, self.path, body)
        response_bytes = json.dumps(payload).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)


def build_http_server(
    host: str,
    port: int,
    *,
    service: InMemoryModuloService,
    runtime: InMemoryWorkerRuntime,
    app: ModuloHTTPApp | None = None,
) -> ThreadingHTTPServer:
    handler_class = type("ModuloRequestHandler", (_ModuloRequestHandler,), {})
    handler_class.app = app or ModuloHTTPApp(service=service, runtime=runtime)
    return ThreadingHTTPServer((host, port), handler_class)
