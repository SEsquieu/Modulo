from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from typing import Protocol
from urllib import error, request

from modulo.common.contracts import ChatRequest
from modulo.worker.errors import WorkerExecutionError


class OllamaHTTPClient(Protocol):
    def chat(self, base_url: str, payload: dict) -> dict:
        """Send a chat request to an Ollama-compatible endpoint."""


@dataclass
class StubExecutor:
    _responses: dict[str, str] = field(default_factory=dict)

    def register_worker(self, worker_id: str, response_text: str) -> None:
        self._responses[worker_id] = response_text

    def execute(self, worker_id: str, request: ChatRequest) -> str:
        del request
        response = self._responses.get(worker_id)
        if response is None:
            raise WorkerExecutionError(f"No execution adapter registered for {worker_id}")
        return response


@dataclass(frozen=True)
class UrllibOllamaHTTPClient:
    timeout_seconds: float = 30.0

    def chat(self, base_url: str, payload: dict) -> dict:
        endpoint = f"{base_url.rstrip('/')}/api/chat"
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except TimeoutError as exc:
            raise WorkerExecutionError("Ollama request timed out") from exc
        except socket.timeout as exc:
            raise WorkerExecutionError("Ollama request timed out") from exc
        except error.URLError as exc:
            raise WorkerExecutionError(f"Ollama request failed: {exc.reason}") from exc

        try:
            parsed = json.loads(body or "{}")
        except json.JSONDecodeError as exc:
            raise WorkerExecutionError("Ollama returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise WorkerExecutionError("Ollama returned a non-object response")
        return parsed


@dataclass(frozen=True)
class OllamaExecutor:
    base_url: str = "http://127.0.0.1:11434"
    http_client: OllamaHTTPClient = UrllibOllamaHTTPClient()

    def execute(self, worker_id: str, request: ChatRequest) -> str:
        del worker_id
        payload = {
            "model": request.model_id,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "stream": request.stream,
        }
        response = self.http_client.chat(self.base_url, payload)
        message = response.get("message")
        if not isinstance(message, dict):
            raise WorkerExecutionError("Ollama response missing assistant message")
        content = message.get("content")
        if not isinstance(content, str):
            raise WorkerExecutionError("Ollama response missing assistant content")
        return content
