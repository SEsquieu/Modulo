import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.common.contracts import ChatMessage, ChatRequest, ExecutionMode
from modulo.worker.errors import WorkerExecutionError
from modulo.worker.executors import OllamaExecutor, StubExecutor


class FakeOllamaHTTPClient:
    def __init__(self, response: dict | None = None, error_message: str | None = None) -> None:
        self.response = response or {
            "message": {"role": "assistant", "content": "hello from ollama"}
        }
        self.error_message = error_message
        self.last_payload: dict | None = None

    def chat(self, base_url: str, payload: dict) -> dict:
        self.last_payload = {"base_url": base_url, "payload": payload}
        if self.error_message is not None:
            raise WorkerExecutionError(self.error_message)
        return self.response


class WorkerExecutorTests(unittest.TestCase):
    def test_stub_executor_returns_registered_response(self) -> None:
        executor = StubExecutor()
        executor.register_worker("worker-1", "stub response")

        response = executor.execute(
            "worker-1",
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK),
        )

        self.assertEqual("stub response", response)

    def test_ollama_executor_sends_messages_and_returns_content(self) -> None:
        http_client = FakeOllamaHTTPClient()
        executor = OllamaExecutor(base_url="http://127.0.0.1:11434", http_client=http_client)

        response = executor.execute(
            "worker-1",
            ChatRequest(
                model_id="llama3.1:8b",
                execution_mode=ExecutionMode.NETWORK,
                messages=(ChatMessage(role="user", content="say hi"),),
            ),
        )

        self.assertEqual("hello from ollama", response)
        self.assertIsNotNone(http_client.last_payload)
        self.assertEqual("http://127.0.0.1:11434", http_client.last_payload["base_url"])
        self.assertEqual("llama3.1:8b", http_client.last_payload["payload"]["model"])
        self.assertEqual("say hi", http_client.last_payload["payload"]["messages"][0]["content"])

    def test_ollama_executor_raises_on_missing_content(self) -> None:
        executor = OllamaExecutor(
            base_url="http://127.0.0.1:11434",
            http_client=FakeOllamaHTTPClient(response={"message": {"role": "assistant"}}),
        )

        with self.assertRaises(WorkerExecutionError):
            executor.execute(
                "worker-1",
                ChatRequest(
                    model_id="llama3.1:8b",
                    execution_mode=ExecutionMode.NETWORK,
                    messages=(ChatMessage(role="user", content="say hi"),),
                ),
            )


if __name__ == "__main__":
    unittest.main()
