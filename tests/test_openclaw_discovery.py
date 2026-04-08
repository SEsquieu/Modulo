import json
import unittest
from pathlib import Path
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.client.openclaw_discovery import OpenClawDiscovery


class OpenClawDiscoveryTests(unittest.TestCase):
    def test_returns_not_installed_when_no_command_or_config_exists(self) -> None:
        config_path = Path("C:/fake/openclaw.json")
        discovery = OpenClawDiscovery(
            modulo_url="http://127.0.0.1:8000",
            config_path=config_path,
            detect_command=False,
        )

        with mock.patch.object(Path, "exists", return_value=False):
            status = discovery.discover()

        self.assertFalse(status.installed)
        self.assertEqual("not_installed", status.state)
        self.assertIn("not detected", status.summary.lower())

    def test_returns_installed_unconfigured_for_non_modulo_base_url(self) -> None:
        config_path = Path("C:/fake/openclaw.json")
        discovery = OpenClawDiscovery(
            modulo_url="http://127.0.0.1:8000",
            config_path=config_path,
            detect_command=False,
        )

        with (
            mock.patch.object(Path, "exists", return_value=True),
            mock.patch.object(
                Path,
                "read_text",
                return_value=json.dumps(
                    {
                        "model": {"primary": "ollama/qwen3.5:4b"},
                        "models": {
                            "providers": {
                                "ollama": {
                                    "baseUrl": "http://127.0.0.1:11434",
                                }
                            }
                        },
                    }
                ),
            ),
        ):
            status = discovery.discover()

        self.assertTrue(status.installed)
        self.assertTrue(status.config_present)
        self.assertFalse(status.configured_for_modulo)
        self.assertEqual("installed_unconfigured", status.state)
        self.assertEqual("ollama", status.current_provider)
        self.assertEqual("ollama/qwen3.5:4b", status.current_primary_model)

    def test_returns_configured_for_matching_modulo_base_url(self) -> None:
        config_path = Path("C:/fake/openclaw.json")
        discovery = OpenClawDiscovery(
            modulo_url="http://127.0.0.1:8000",
            config_path=config_path,
            detect_command=False,
        )

        with (
            mock.patch.object(Path, "exists", return_value=True),
            mock.patch.object(
                Path,
                "read_text",
                return_value=json.dumps(
                    {
                        "model": {"primary": "ollama/llama3.1:8b"},
                        "models": {
                            "providers": {
                                "ollama": {
                                    "baseUrl": "http://127.0.0.1:8000",
                                }
                            }
                        },
                    }
                ),
            ),
        ):
            status = discovery.discover()

        self.assertTrue(status.installed)
        self.assertTrue(status.config_present)
        self.assertTrue(status.configured_for_modulo)
        self.assertEqual("configured", status.state)
        self.assertIn("configured to route through modulo", status.summary.lower())


if __name__ == "__main__":
    unittest.main()
