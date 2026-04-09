import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.client.ollama_loaded_models import OllamaLoadedModelsDiscovery


class FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False

    def read(self) -> bytes:
        return self.payload


class OllamaLoadedModelsDiscoveryTests(unittest.TestCase):
    def test_returns_loaded_models_from_api_payload(self) -> None:
        discovery = OllamaLoadedModelsDiscovery()
        payload = {
            "models": [
                {
                    "name": "qwen3.5:4b",
                    "model": "qwen3.5:4b",
                    "size": 1234,
                    "size_vram": 4321,
                    "expires_at": "2099-01-01T00:00:00Z",
                    "context_length": 8192,
                    "details": {
                        "family": "qwen3",
                        "parameter_size": "4.0B",
                        "quantization_level": "Q4_K_M",
                    },
                }
            ]
        }

        with mock.patch(
            "modulo.client.ollama_loaded_models.request.urlopen",
            return_value=FakeHTTPResponse(payload),
        ):
            status = discovery.discover()

        self.assertTrue(status.available)
        self.assertEqual(1, len(status.loaded_models))
        self.assertEqual("qwen3.5:4b", status.loaded_models[0].model_id)
        self.assertEqual(4321, status.loaded_models[0].size_vram_bytes)
        self.assertEqual(8192, status.loaded_models[0].context_length)

    def test_returns_empty_loaded_state_when_no_models_are_loaded(self) -> None:
        discovery = OllamaLoadedModelsDiscovery()

        with mock.patch(
            "modulo.client.ollama_loaded_models.request.urlopen",
            return_value=FakeHTTPResponse({"models": []}),
        ):
            status = discovery.discover()

        self.assertTrue(status.available)
        self.assertEqual((), status.loaded_models)
        self.assertIn("no ollama models", status.summary.lower())

    def test_returns_unavailable_state_when_runtime_is_unreachable(self) -> None:
        discovery = OllamaLoadedModelsDiscovery()

        with mock.patch(
            "modulo.client.ollama_loaded_models.request.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            status = discovery.discover()

        self.assertFalse(status.available)
        self.assertIn("timed out", status.summary.lower())


if __name__ == "__main__":
    unittest.main()
