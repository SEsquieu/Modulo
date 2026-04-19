from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from typing import Iterator, Protocol
from urllib import error, request

from modulo.common.contracts import ChatRequest, ChatStreamEvent, ChatStreamEventType
from modulo.worker.errors import WorkerExecutionError


class OllamaHTTPClient(Protocol):
    def chat(self, base_url: str, payload: dict) -> dict:
        """Send a chat request to an Ollama-compatible endpoint."""

    def chat_stream(self, base_url: str, payload: dict) -> Iterator[dict]:
        """Send a streaming chat request to an Ollama-compatible endpoint."""


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

    def execute_stream(self, worker_id: str, request: ChatRequest) -> Iterator[ChatStreamEvent]:
        response = self.execute(worker_id, request)
        yield ChatStreamEvent(
            event_type=ChatStreamEventType.START,
            model_id=request.model_id,
        )
        if response:
            yield ChatStreamEvent(
                event_type=ChatStreamEventType.TOKEN,
                model_id=request.model_id,
                content=response,
            )
        yield ChatStreamEvent(
            event_type=ChatStreamEventType.END,
            model_id=request.model_id,
        )


@dataclass(frozen=True)
class UrllibOllamaHTTPClient:
    timeout_seconds: float = 120.0

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

    def chat_stream(self, base_url: str, payload: dict) -> Iterator[dict]:
        endpoint = f"{base_url.rstrip('/')}/api/chat"
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise WorkerExecutionError("Ollama returned invalid streaming JSON") from exc
                    if not isinstance(parsed, dict):
                        raise WorkerExecutionError("Ollama returned a non-object streaming event")
                    yield parsed
        except TimeoutError as exc:
            raise WorkerExecutionError("Ollama request timed out") from exc
        except socket.timeout as exc:
            raise WorkerExecutionError("Ollama request timed out") from exc
        except error.URLError as exc:
            raise WorkerExecutionError(f"Ollama request failed: {exc.reason}") from exc


@dataclass(frozen=True)
class OllamaExecutor:
    base_url: str = "http://127.0.0.1:11434"
    http_client: OllamaHTTPClient = UrllibOllamaHTTPClient()
    think: bool | str | None = False

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
        if self.think is not None:
            payload["think"] = self.think
        response = self.http_client.chat(self.base_url, payload)
        message = response.get("message")
        if not isinstance(message, dict):
            raise WorkerExecutionError("Ollama response missing assistant message")
        content = message.get("content")
        if not isinstance(content, str):
            raise WorkerExecutionError("Ollama response missing assistant content")
        return content

    def execute_stream(self, worker_id: str, request: ChatRequest) -> Iterator[ChatStreamEvent]:
        if not hasattr(self.http_client, "chat_stream"):
            response = self.execute(worker_id, request)
            yield ChatStreamEvent(
                event_type=ChatStreamEventType.START,
                model_id=request.model_id,
            )
            if response:
                yield ChatStreamEvent(
                    event_type=ChatStreamEventType.TOKEN,
                    model_id=request.model_id,
                    content=response,
                )
            yield ChatStreamEvent(
                event_type=ChatStreamEventType.END,
                model_id=request.model_id,
            )
            return
        del worker_id
        payload = {
            "model": request.model_id,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "stream": True,
        }
        if self.think is not None:
            payload["think"] = self.think
        yield ChatStreamEvent(
            event_type=ChatStreamEventType.START,
            model_id=request.model_id,
        )
        for event in self.http_client.chat_stream(self.base_url, payload):
            message = event.get("message", {})
            if not isinstance(message, dict):
                message = {}
            content = message.get("content", "")
            if isinstance(content, str) and content:
                yield ChatStreamEvent(
                    event_type=ChatStreamEventType.TOKEN,
                    model_id=request.model_id,
                    content=content,
                )
            if bool(event.get("done", False)):
                yield ChatStreamEvent(
                    event_type=ChatStreamEventType.END,
                    model_id=request.model_id,
                )
                return
        yield ChatStreamEvent(
            event_type=ChatStreamEventType.END,
            model_id=request.model_id,
        )
