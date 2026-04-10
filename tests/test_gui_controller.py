import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.gui.controller import GuiAppController
from modulo.client.app import HostingPrewarmResult
from modulo.client.ollama_discovery import OllamaDiscoveryStatus
from modulo.client.ollama_loaded_models import LoadedOllamaModel, OllamaLoadedModelsStatus
from modulo.client.openclaw_discovery import OpenClawDiscoveryStatus
from modulo.client.hosting_readiness import HostingRuntimeProbeStatus
from modulo.prototype import LocalPrototypeHarness


class FakeGuiOllamaDiscovery:
    def discover(self) -> OllamaDiscoveryStatus:
        return OllamaDiscoveryStatus(
            available=True,
            installed_model_ids=("qwen3.5:4b",),
            summary="Ollama is available with 1 local model.",
            details="fake gui discovery",
        )


class FakeGuiHostingRuntimeProbe:
    def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
        return HostingRuntimeProbeStatus(
            reachable=False,
            model_ready=False,
            summary=f"runtime probe failed for {model_id}",
            detail="no local runtime match",
            error="no local runtime match",
        )


class FakeGuiOpenClawDiscovery:
    def discover(self) -> OpenClawDiscoveryStatus:
        return OpenClawDiscoveryStatus(
            installed=False,
            config_present=False,
            configured_for_modulo=False,
            state="not_installed",
            summary="OpenClaw was not detected on this machine.",
            details="No OpenClaw install or config footprint was found.",
        )


class FakeGuiLoadedModelsDiscovery:
    def discover(self) -> OllamaLoadedModelsStatus:
        return OllamaLoadedModelsStatus(
            available=True,
            loaded_models=(
                LoadedOllamaModel(
                    model_id="llama3.1:8b",
                    display_name="llama3.1:8b",
                    expires_at="2099-01-01T00:00:00Z",
                    size_vram_bytes=4096,
                ),
            ),
            summary="1 Ollama model is currently loaded in memory.",
            details="fake gui loaded discovery",
        )


class MutableGuiLoadedModelsDiscovery:
    def __init__(self) -> None:
        self.loaded_models: tuple[LoadedOllamaModel, ...] = ()

    def discover(self) -> OllamaLoadedModelsStatus:
        return OllamaLoadedModelsStatus(
            available=True,
            loaded_models=self.loaded_models,
            summary=(
                "No Ollama models are currently loaded in memory."
                if not self.loaded_models
                else f"{len(self.loaded_models)} Ollama model(s) are currently loaded in memory."
            ),
            details="mutable gui loaded discovery",
        )


class SuccessfulGuiPrewarmer:
    def __init__(self, loaded_discovery: MutableGuiLoadedModelsDiscovery) -> None:
        self.loaded_discovery = loaded_discovery

    def prewarm(self, model_id: str) -> HostingPrewarmResult:
        self.loaded_discovery.loaded_models = (
            LoadedOllamaModel(
                model_id=model_id,
                display_name=model_id,
                expires_at="2099-01-01T00:00:00Z",
                size_vram_bytes=2048,
            ),
        )
        return HostingPrewarmResult(
            ok=True,
            summary=f"Prewarm requested for {model_id}.",
            detail="fake gui prewarm success",
        )


class FailedGuiPrewarmer:
    def prewarm(self, model_id: str) -> HostingPrewarmResult:
        return HostingPrewarmResult(
            ok=False,
            summary=f"Prewarm failed for {model_id}.",
            detail="fake gui prewarm failure",
        )


class ReadyGuiHostingRuntimeProbe:
    def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
        return HostingRuntimeProbeStatus(
            reachable=True,
            model_ready=True,
            summary=f"runtime probe passed for {model_id}",
            detail="local runtime is ready",
        )


class FakeGuiOllamaHTTPClient:
    def chat(self, base_url: str, payload: dict) -> dict:
        del base_url
        return {
            "message": {
                "content": f"real gui response for {payload['model']}",
            }
        }


class InstalledGuiOpenClawDiscovery:
    def discover(self) -> OpenClawDiscoveryStatus:
        return OpenClawDiscoveryStatus(
            installed=True,
            config_present=True,
            configured_for_modulo=False,
            state="installed_unconfigured",
            summary="OpenClaw is installed, but the local config is not routing through Modulo.",
            details="Config path: C:\\Users\\test\\.openclaw\\openclaw.json",
            current_primary_model="ollama/llama3.1:8b",
            current_provider="ollama",
            current_base_url="http://127.0.0.1:11434",
        )


class BrokenGuiOpenClawDiscovery:
    def discover(self) -> OpenClawDiscoveryStatus:
        return OpenClawDiscoveryStatus(
            installed=True,
            config_present=True,
            configured_for_modulo=False,
            state="installed_unconfigured",
            summary="OpenClaw config was found, but it could not be read cleanly.",
            details="Config path: C:\\Users\\test\\.openclaw\\openclaw.json\nRead error: Expecting property name",
            error="Expecting property name enclosed in double quotes",
        )


class GuiAppControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = GuiAppController(
            harness=LocalPrototypeHarness(
                openclaw_discovery=FakeGuiOpenClawDiscovery(),
                ollama_discovery=FakeGuiOllamaDiscovery(),
                ollama_loaded_models_discovery=FakeGuiLoadedModelsDiscovery(),
                hosting_runtime_probe=FakeGuiHostingRuntimeProbe(),
            )
        )

    def test_refresh_reports_initial_shell_state(self) -> None:
        state = self.controller.refresh()

        self.assertTrue(state.connected_to_modulo)
        self.assertFalse(state.openclaw_configured)
        self.assertFalse(state.hosting_enabled)
        self.assertTrue(state.connect_action_enabled)
        self.assertEqual("Configure OpenClaw", state.openclaw_action_label)
        self.assertEqual("NOT INSTALLED", state.openclaw_status_badge)
        self.assertFalse(state.openclaw_plan_apply_enabled)
        self.assertTrue(state.start_action_enabled)
        self.assertFalse(state.stop_action_enabled)
        self.assertTrue(state.smoke_action_enabled)
        self.assertIn("managed separately", state.home_subtitle)
        self.assertIn("not configured", state.connection_summary.lower())
        self.assertIn("not configured", state.openclaw_summary.lower())
        self.assertIn("not changing local OpenClaw", state.openclaw_details)
        self.assertIn("Safe prototype mode", state.openclaw_safety_note)
        self.assertEqual("SETUP NEEDED", state.openclaw_guidance_badge)
        self.assertIn("install openclaw first", state.openclaw_guidance_summary.lower())
        self.assertTrue(state.openclaw_next_steps)
        self.assertIn("not installed", state.openclaw_plan_summary.lower())
        self.assertIn("No network models", state.buyer_platform_summary)
        self.assertIn("local-only", state.buyer_account_summary)
        self.assertIn("Prototype credits", state.buyer_credits_summary)
        self.assertIn("platform-managed", state.buyer_config_summary)
        self.assertEqual(("No network models available yet.",), state.buyer_network_models)
        self.assertTrue(state.buyer_cloud_models)
        self.assertEqual("qwen3.5:4b", state.hosting_selected_model_id)
        self.assertEqual(("qwen3.5:4b",), state.hosting_available_model_ids)
        self.assertEqual(
            ("🖥 qwen3.5:4b (local)",),
            state.hosting_available_model_labels,
        )
        self.assertEqual((), state.hosting_supported_installed_model_ids)
        self.assertEqual(("llama3.1:8b",), state.hosting_supported_missing_model_ids)
        self.assertEqual(("qwen3.5:4b",), state.hosting_unsupported_installed_model_ids)
        self.assertEqual("Prototype", state.hosting_mode_badge)
        self.assertEqual("COLD", state.hosting_warm_state_badge)
        self.assertIn("not currently loaded", state.hosting_warm_summary)
        self.assertTrue(state.hosting_warm_details)
        self.assertEqual("PROTOTYPE", state.execution_mode_badge)
        self.assertIn("prototype-safe", state.execution_summary)
        self.assertEqual("AVAILABLE", state.ollama_status_badge)
        self.assertIn("Ollama is available locally", state.ollama_summary)
        self.assertIn("1 installed model(s) outside the curated catalog", state.ollama_inventory_summary)
        self.assertTrue(state.hosting_setup_action_enabled)
        self.assertEqual("BLOCKED", state.hosting_readiness_badge)
        self.assertIn("could not resolve", state.hosting_preflight_summary)
        self.assertEqual("no local runtime match", state.hosting_preflight_reason)
        self.assertIn("PASS: The selected local Ollama model is installed locally.", state.hosting_preflight_checks)
        self.assertTrue(state.start_action_enabled)
        self.assertIn("Prototype hosting is available", state.hosting_setup_summary)
        self.assertIn("Hosting mode: prototype-safe demo path.", state.hosting_setup_details)
        self.assertIn("Not registered", state.worker_registration_text)
        self.assertIn("idle", state.worker_health_summary.lower())
        self.assertIn("not processed a job", state.worker_activity_summary)
        self.assertEqual("Constrained GUI smoke probe", state.smoke_test_prompt)
        self.assertEqual("Not run yet", state.smoke_test_result_label)
        self.assertIn("Run a smoke test", state.diagnostics_summary)
        self.assertIn("Last worker error: None", state.diagnostics_details)
        self.assertIn("No buyer continuity activity yet.", state.continuity_summary)
        self.assertEqual(("No recent activity yet.",), state.activity_lines)
        self.assertEqual("Enable Hosting", state.secondary_action_label)
        self.assertEqual("stopped", state.worker_runtime_state)
        self.assertEqual("No smoke test run yet.", state.smoke_test_summary)

    def test_start_hosting_and_smoke_test_update_state(self) -> None:
        self.controller = GuiAppController(
            harness=LocalPrototypeHarness(
                openclaw_discovery=InstalledGuiOpenClawDiscovery(),
                ollama_discovery=FakeGuiOllamaDiscovery(),
                ollama_loaded_models_discovery=FakeGuiLoadedModelsDiscovery(),
                hosting_runtime_probe=FakeGuiHostingRuntimeProbe(),
            )
        )
        self.controller.configure_openclaw()
        self.controller.apply_openclaw_connection()
        started = self.controller.start_hosting()
        smoked = self.controller.run_smoke_test()

        self.assertTrue(started.hosting_enabled)
        self.assertTrue(started.worker_registered)
        self.assertTrue(started.worker_healthy)
        self.assertEqual("Review OpenClaw Setup", started.openclaw_action_label)
        self.assertEqual("CONFIGURED", started.openclaw_status_badge)
        self.assertEqual("READY", started.openclaw_guidance_badge)
        self.assertIn("use routing is staged", started.openclaw_guidance_summary.lower())
        self.assertIn("configured", started.openclaw_summary.lower())
        self.assertIn("without editing local OpenClaw files", started.openclaw_details)
        self.assertTrue(started.buyer_network_models)
        self.assertIn("currently advertised", started.buyer_platform_summary)
        self.assertIn("platform-managed", started.buyer_config_summary)
        self.assertFalse(started.start_action_enabled)
        self.assertTrue(started.stop_action_enabled)
        self.assertTrue(started.restart_action_enabled)
        self.assertTrue(started.smoke_action_enabled)
        self.assertIn("Hosting is enabled", started.hosting_summary)
        self.assertEqual("COLD", started.hosting_warm_state_badge)
        self.assertTrue(smoked.smoke_test_ok)
        self.assertEqual("PASS", smoked.smoke_status_badge)
        self.assertIn("Smoke test passed", smoked.smoke_test_summary)
        self.assertIn("via PROTOTYPE execution", smoked.smoke_test_summary)
        self.assertIn("Probe: Constrained GUI smoke probe", smoked.smoke_test_details)
        self.assertIn("Execution mode: PROTOTYPE", smoked.smoke_test_details)
        self.assertEqual("Constrained GUI smoke probe", smoked.smoke_test_prompt)
        self.assertEqual("Pass", smoked.smoke_test_result_label)
        self.assertIn("diagnostics look healthy", smoked.diagnostics_summary)
        self.assertIn("Response:", smoked.diagnostics_details)
        self.assertIn("Execution mode: PROTOTYPE", smoked.diagnostics_details)
        self.assertIn("Latest routing sent", smoked.continuity_summary)
        self.assertTrue(smoked.activity_lines)
        self.assertTrue(smoked.last_job_id)
        self.assertEqual("completed", smoked.last_job_status)
        self.assertIn("finished with status completed", smoked.worker_activity_summary)

    def test_real_execution_mode_surfaces_in_gui_state(self) -> None:
        self.controller = GuiAppController(
            harness=LocalPrototypeHarness(
                openclaw_discovery=InstalledGuiOpenClawDiscovery(),
                ollama_discovery=FakeGuiOllamaDiscovery(),
                ollama_loaded_models_discovery=FakeGuiLoadedModelsDiscovery(),
                hosting_runtime_probe=ReadyGuiHostingRuntimeProbe(),
                ollama_http_client=FakeGuiOllamaHTTPClient(),
            )
        )

        initial = self.controller.refresh()
        smoked = self.controller.run_smoke_test()

        self.assertEqual("Ollama", initial.hosting_mode_badge)
        self.assertEqual("COLD", initial.hosting_warm_state_badge)
        self.assertEqual("REAL", initial.execution_mode_badge)
        self.assertIn("ready for real local execution", initial.execution_summary.lower())
        self.assertTrue(smoked.smoke_test_ok)
        self.assertIn("via REAL execution", smoked.smoke_test_summary)
        self.assertIn("Probe: Constrained GUI smoke probe", smoked.smoke_test_details)
        self.assertIn("Execution mode: REAL", smoked.smoke_test_details)
        self.assertIn("runtime probe passed", smoked.smoke_test_details)
        self.assertEqual("REAL", smoked.execution_mode_badge)
        self.assertIn("runtime probe passed", smoked.execution_summary)

    def test_configure_openclaw_stages_plan_before_apply(self) -> None:
        self.controller = GuiAppController(
            harness=LocalPrototypeHarness(
                openclaw_discovery=InstalledGuiOpenClawDiscovery(),
                ollama_discovery=FakeGuiOllamaDiscovery(),
                ollama_loaded_models_discovery=FakeGuiLoadedModelsDiscovery(),
                hosting_runtime_probe=FakeGuiHostingRuntimeProbe(),
            )
        )
        staged = self.controller.configure_openclaw()

        self.assertFalse(staged.openclaw_configured)
        self.assertEqual("READY TO APPLY", staged.openclaw_guidance_badge)
        self.assertIn("review the staged routing plan", staged.openclaw_guidance_summary.lower())
        self.assertIn("plan", staged.openclaw_plan_summary.lower())
        self.assertTrue(staged.openclaw_plan_changes)

    def test_parse_error_state_surfaces_attention_guidance(self) -> None:
        self.controller = GuiAppController(
            harness=LocalPrototypeHarness(
                openclaw_discovery=BrokenGuiOpenClawDiscovery(),
                ollama_discovery=FakeGuiOllamaDiscovery(),
                ollama_loaded_models_discovery=FakeGuiLoadedModelsDiscovery(),
                hosting_runtime_probe=FakeGuiHostingRuntimeProbe(),
            )
        )

        state = self.controller.refresh()

        self.assertEqual("ATTENTION", state.openclaw_guidance_badge)
        self.assertIn("could not parse", state.openclaw_guidance_summary.lower())
        self.assertTrue(any("fix the config parse/read issue" in step.lower() for step in state.openclaw_next_steps))
        self.assertIn("Read error:", state.openclaw_details)

    def test_apply_openclaw_connection_marks_setup_as_configured(self) -> None:
        self.controller = GuiAppController(
            harness=LocalPrototypeHarness(
                openclaw_discovery=InstalledGuiOpenClawDiscovery(),
                ollama_discovery=FakeGuiOllamaDiscovery(),
                ollama_loaded_models_discovery=FakeGuiLoadedModelsDiscovery(),
                hosting_runtime_probe=FakeGuiHostingRuntimeProbe(),
            )
        )
        self.controller.configure_openclaw()
        configured = self.controller.apply_openclaw_connection()

        self.assertTrue(configured.openclaw_configured)
        self.assertEqual("Review OpenClaw Setup", configured.openclaw_action_label)
        self.assertEqual("CONFIGURED", configured.openclaw_status_badge)

    def test_select_hosting_model_updates_setup_state(self) -> None:
        self.controller = GuiAppController(
            harness=LocalPrototypeHarness(
                openclaw_discovery=FakeGuiOpenClawDiscovery(),
                ollama_discovery=FakeGuiOllamaDiscovery(),
                ollama_loaded_models_discovery=FakeGuiLoadedModelsDiscovery(),
                hosting_runtime_probe=ReadyGuiHostingRuntimeProbe(),
            )
        )
        state = self.controller.select_hosting_model("qwen3.5:4b")

        self.assertEqual("qwen3.5:4b", state.hosting_selected_model_id)
        self.assertEqual("READY", state.hosting_readiness_badge)
        self.assertEqual("COLD", state.hosting_warm_state_badge)
        self.assertIn("Hosting preflight passed", state.hosting_setup_summary)

    def test_start_hosting_shows_warm_failed_when_prewarm_fails(self) -> None:
        loaded_discovery = MutableGuiLoadedModelsDiscovery()
        self.controller = GuiAppController(
            harness=LocalPrototypeHarness(
                openclaw_discovery=FakeGuiOpenClawDiscovery(),
                ollama_discovery=FakeGuiOllamaDiscovery(),
                ollama_loaded_models_discovery=loaded_discovery,
                hosting_runtime_probe=ReadyGuiHostingRuntimeProbe(),
                hosting_prewarmer=FailedGuiPrewarmer(),
                ollama_http_client=FakeGuiOllamaHTTPClient(),
            )
        )

        started = self.controller.start_hosting()

        self.assertEqual("WARM_FAILED", started.hosting_warm_state_badge)
        self.assertIn("prewarm failed", started.hosting_warm_summary.lower())

    def test_debug_state_surfaces_cross_network_commands(self) -> None:
        state = self.controller.refresh()

        self.assertIn("http://127.0.0.1:", state.debug_platform_url)
        self.assertTrue(state.debug_target_url)
        self.assertEqual("prototype-private", state.debug_private_network_id)
        self.assertTrue(state.debug_worker_id)
        self.assertTrue(state.debug_model_id)
        self.assertTrue(state.debug_topology_lines)
        self.assertIn("modulo.worker.bridge_runner", state.debug_worker_command)
        self.assertIn("--scope private", state.debug_worker_command)
        self.assertIn("Invoke-RestMethod", state.debug_request_command)
        self.assertIn("/api/chat", state.debug_request_command)

    def test_debug_probe_can_hit_current_platform_target(self) -> None:
        state = self.controller.run_debug_probe()

        self.assertEqual("Pass", state.debug_probe_result_label)
        self.assertIn("returned", state.debug_probe_summary)
        self.assertIn("Execution mode: NETWORK", state.debug_probe_details)
        self.assertIn("Response:", state.debug_probe_details)

    def test_debug_target_updates_use_visibility_from_remote_platform(self) -> None:
        host_harness = LocalPrototypeHarness(
            model_id="gemma4:e2b",
            openclaw_discovery=InstalledGuiOpenClawDiscovery(),
            ollama_discovery=FakeGuiOllamaDiscovery(),
            ollama_loaded_models_discovery=FakeGuiLoadedModelsDiscovery(),
            hosting_runtime_probe=FakeGuiHostingRuntimeProbe(),
        )
        buyer_controller = GuiAppController(
            harness=LocalPrototypeHarness(
                openclaw_discovery=InstalledGuiOpenClawDiscovery(),
                ollama_discovery=FakeGuiOllamaDiscovery(),
                ollama_loaded_models_discovery=FakeGuiLoadedModelsDiscovery(),
                hosting_runtime_probe=FakeGuiHostingRuntimeProbe(),
            )
        )

        try:
            host_harness.client.set_hosting_model("gemma4:e2b")
            host_harness.boot()

            state = buyer_controller.set_debug_target_url(host_harness.modulo_url)

            self.assertIn("currently advertised", state.buyer_platform_summary)
            self.assertTrue(any("gemma4:e2b" in line for line in state.buyer_network_models))
            self.assertIn("network:gemma4:e2b", state.use_available_model_ids)
            self.assertIn(host_harness.modulo_url, state.debug_summary)
        finally:
            buyer_controller.harness.shutdown()
            host_harness.shutdown()


if __name__ == "__main__":
    unittest.main()
