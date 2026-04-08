import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.client.ollama_discovery import OllamaDiscovery, OllamaDiscoveryStatus


class OllamaDiscoveryTests(unittest.TestCase):
    def test_parse_models_skips_header_and_preserves_names(self) -> None:
        output = (
            "NAME            ID              SIZE    MODIFIED\n"
            "llama3.1:8b     abc123          4 GB    2 hours ago\n"
            "mistral:7b      def456          5 GB    1 hour ago\n"
        )

        models = OllamaDiscovery._parse_models(output)

        self.assertEqual(("llama3.1:8b", "mistral:7b"), models)

    def test_parse_models_handles_empty_output(self) -> None:
        self.assertEqual((), OllamaDiscovery._parse_models(""))

    def test_status_dataclass_defaults_are_safe(self) -> None:
        status = OllamaDiscoveryStatus()

        self.assertFalse(status.available)
        self.assertEqual((), status.installed_model_ids)
        self.assertIn("not available", status.summary.lower())


if __name__ == "__main__":
    unittest.main()
