import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.common.contracts import WorkerKind, WorkerModelState, WorkerSnapshot
from modulo.service.execution import InMemoryWorkerRuntime
from modulo.service.http import ModuloHTTPApp
from modulo.service.router import TrustRouter
from modulo.service.runtime import InMemoryModuloService


class ModuloHTTPAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InMemoryModuloService(router=TrustRouter())
        self.runtime = InMemoryWorkerRuntime()
        self.app = ModuloHTTPApp(service=self.service, runtime=self.runtime)

        self.service.register_worker(
            WorkerSnapshot(
                worker_id="network-1",
                kind=WorkerKind.NETWORK,
                healthy=True,
                max_concurrency=1,
                advertised_models=(
                    WorkerModelState(
                        model_id="llama3.1:8b",
                        runtime_identity="llama3.1:8b",
                    ),
                ),
            )
        )
        self.runtime.register_worker("network-1", "hello from modulo")

    def test_get_tags_returns_supported_models(self) -> None:
        status, payload = self.app.handle("GET", "/api/tags")
        self.assertEqual(200, status)
        self.assertEqual("llama3.1:8b", payload["models"][0]["name"])

    def test_post_chat_returns_ollama_shaped_response(self) -> None:
        status, payload = self.app.handle(
            "POST",
            "/api/chat",
            json.dumps(
                {
                    "model": "llama3.1:8b",
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                }
            ).encode("utf-8"),
        )
        self.assertEqual(200, status)
        self.assertEqual("llama3.1:8b", payload["model"])
        self.assertEqual("assistant", payload["message"]["role"])
        self.assertEqual("hello from modulo", payload["message"]["content"])
        self.assertTrue(payload["done"])

    def test_post_chat_rejects_missing_model(self) -> None:
        status, payload = self.app.handle(
            "POST",
            "/api/chat",
            json.dumps({"messages": [{"role": "user", "content": "hi"}]}).encode("utf-8"),
        )
        self.assertEqual(400, status)
        self.assertIn("model", payload["error"])

    def test_post_chat_returns_gateway_error_when_runtime_missing(self) -> None:
        self.runtime = InMemoryWorkerRuntime()
        self.app = ModuloHTTPApp(service=self.service, runtime=self.runtime)

        status, payload = self.app.handle(
            "POST",
            "/api/chat",
            json.dumps({"model": "llama3.1:8b", "messages": []}).encode("utf-8"),
        )
        self.assertEqual(502, status)
        self.assertIn("No execution adapter", payload["error"])


if __name__ == "__main__":
    unittest.main()
