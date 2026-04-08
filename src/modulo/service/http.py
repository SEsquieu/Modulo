from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from modulo.common.catalog import SUPPORTED_MODELS
from modulo.common.contracts import ChatRequest, ExecutionMode, JobResult
from modulo.service.execution import InMemoryWorkerRuntime, WorkerExecutionError
from modulo.service.jobs import JobQueueError
from modulo.service.router import RoutingError
from modulo.service.runtime import InMemoryModuloService


@dataclass
class ModuloHTTPApp:
    service: InMemoryModuloService
    runtime: InMemoryWorkerRuntime

    def handle(self, method: str, path: str, body: bytes | None = None) -> tuple[int, dict[str, Any]]:
        if method == "GET" and path == "/api/tags":
            return HTTPStatus.OK, self._handle_tags()

        if method == "POST" and path == "/api/chat":
            try:
                payload = json.loads((body or b"{}").decode("utf-8"))
            except json.JSONDecodeError:
                return HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload"}
            return self._handle_chat(payload)

        return HTTPStatus.NOT_FOUND, {"error": "Not found"}

    def _handle_tags(self) -> dict[str, Any]:
        return {
            "models": [
                {
                    "name": model.model_id,
                    "model": model.model_id,
                }
                for model in SUPPORTED_MODELS.values()
            ]
        }

    def _handle_chat(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        model_id = payload.get("model")
        if not isinstance(model_id, str) or not model_id:
            return HTTPStatus.BAD_REQUEST, {"error": "Missing required field: model"}

        request = ChatRequest(
            model_id=model_id,
            execution_mode=ExecutionMode.NETWORK,
            stream=bool(payload.get("stream", False)),
            requires_tools=bool(payload.get("tools")),
        )

        try:
            job = self.service.submit_chat(request)
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
) -> ThreadingHTTPServer:
    handler_class = type("ModuloRequestHandler", (_ModuloRequestHandler,), {})
    handler_class.app = ModuloHTTPApp(service=service, runtime=runtime)
    return ThreadingHTTPServer((host, port), handler_class)
