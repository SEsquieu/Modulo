from __future__ import annotations

from dataclasses import dataclass

from modulo.client.app import ClientStatus, ModuloClientSupervisor, OnboardingStatus, SmokeTestResult
from modulo.common.contracts import WorkerRuntimeState, WorkerStatusSnapshot
from modulo.prototype import (
    GUI_SMOKE_TEST_SYSTEM_PROMPT,
    GUI_SMOKE_TEST_USER_PROMPT,
    LocalPrototypeHarness,
)


@dataclass(frozen=True)
class GuiShellState:
    connected_to_modulo: bool
    openclaw_configured: bool
    hosting_enabled: bool
    worker_registered: bool
    worker_healthy: bool
    home_title: str = "Modulo"
    home_subtitle: str = ""
    connection_summary: str = ""
    hosting_summary: str = ""
    smoke_status_badge: str = ""
    worker_status_badge: str = ""
    primary_action_label: str = ""
    secondary_action_label: str = ""
    connect_action_enabled: bool = True
    openclaw_action_label: str = "Configure OpenClaw"
    openclaw_status_badge: str = "NOT INSTALLED"
    openclaw_summary: str = ""
    openclaw_details: str = ""
    openclaw_safety_note: str = ""
    openclaw_guidance_badge: str = "INFO"
    openclaw_guidance_summary: str = ""
    openclaw_next_steps: tuple[str, ...] = ()
    openclaw_plan_summary: str = ""
    openclaw_plan_details: str = ""
    openclaw_plan_changes: tuple[str, ...] = ()
    openclaw_plan_apply_enabled: bool = False
    openclaw_plan_apply_label: str = "Apply staged plan"
    buyer_platform_summary: str = ""
    buyer_account_summary: str = ""
    buyer_network_models: tuple[str, ...] = ()
    buyer_cloud_models: tuple[str, ...] = ()
    buyer_credits_summary: str = ""
    buyer_config_summary: str = ""
    use_status_badge: str = "SETUP"
    use_summary: str = ""
    use_selected_model_id: str = ""
    use_available_model_ids: tuple[str, ...] = ()
    use_available_model_labels: tuple[str, ...] = ()
    use_selected_model_label: str = ""
    use_selected_model_source: str = ""
    use_route_target: str = ""
    use_provider_label: str = ""
    use_route_health_value: str = "Setup"
    use_route_health_summary: str = ""
    mount_selected_shape_id: str = ""
    mount_available_shape_ids: tuple[str, ...] = ()
    mount_available_shape_labels: tuple[str, ...] = ()
    mount_selected_shape_label: str = ""
    mount_selected_consumer_id: str = ""
    mount_available_consumer_ids: tuple[str, ...] = ()
    mount_available_consumer_labels: tuple[str, ...] = ()
    use_mount_status_value: str = "Not configured"
    use_mount_status_summary: str = ""
    mount_consumer_label: str = "Not selected"
    mount_consumer_summary: str = ""
    mount_detail_lines: tuple[str, ...] = ()
    use_route_details: tuple[str, ...] = ()
    use_local_model_lines: tuple[str, ...] = ()
    use_private_model_lines: tuple[str, ...] = ()
    use_public_model_lines: tuple[str, ...] = ()
    hosting_selected_model_id: str = ""
    hosting_available_model_ids: tuple[str, ...] = ()
    hosting_available_model_labels: tuple[str, ...] = ()
    hosting_supported_installed_model_ids: tuple[str, ...] = ()
    hosting_supported_missing_model_ids: tuple[str, ...] = ()
    hosting_unsupported_installed_model_ids: tuple[str, ...] = ()
    hosting_mode_badge: str = "OLLAMA"
    hosting_warm_state_badge: str = "UNKNOWN"
    hosting_warm_summary: str = ""
    hosting_warm_details: tuple[str, ...] = ()
    ollama_status_badge: str = "UNAVAILABLE"
    ollama_summary: str = ""
    ollama_inventory_summary: str = ""
    hosting_readiness_badge: str = "BLOCKED"
    hosting_preflight_summary: str = ""
    hosting_preflight_reason: str = ""
    hosting_preflight_checks: tuple[str, ...] = ()
    hosting_setup_summary: str = ""
    hosting_setup_details: str = ""
    hosting_setup_action_enabled: bool = True
    execution_mode_badge: str = "PROTOTYPE"
    execution_summary: str = ""
    start_action_enabled: bool = True
    stop_action_enabled: bool = False
    restart_action_enabled: bool = False
    smoke_action_enabled: bool = False
    worker_registration_text: str = ""
    worker_health_summary: str = ""
    worker_activity_summary: str = ""
    worker_id: str = ""
    worker_runtime_state: str = ""
    enabled_models_text: str = ""
    current_load: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    last_job_id: str = ""
    last_job_status: str = ""
    last_worker_error: str = ""
    smoke_test_ok: bool = False
    smoke_test_prompt: str = "Constrained GUI smoke probe"
    smoke_test_summary: str = "No smoke test run yet."
    smoke_test_details: str = ""
    smoke_test_result_label: str = "Not run yet"
    diagnostics_summary: str = ""
    diagnostics_details: str = ""
    route_trace_result_label: str = "Not captured"
    route_trace_summary: str = "No routed execution trace is available yet."
    route_trace_details: str = ""
    continuity_summary: str = ""
    activity_lines: tuple[str, ...] = ()
    debug_status_badge: str = "DEBUG"
    debug_summary: str = ""
    debug_platform_url: str = ""
    debug_target_url: str = ""
    debug_lan_platform_url: str = ""
    debug_private_network_id: str = ""
    debug_worker_id: str = ""
    debug_model_id: str = ""
    debug_topology_lines: tuple[str, ...] = ()
    debug_worker_command: str = ""
    debug_request_command: str = ""
    debug_probe_result_label: str = "Not run yet"
    debug_probe_summary: str = "No debug network probe has run yet."
    debug_probe_details: str = ""


@dataclass
class GuiAppController:
    harness: LocalPrototypeHarness
    _last_smoke_test_prompt: str = "Constrained GUI smoke probe"
    _selected_model_id: str = ""
    _selected_use_model_id: str = ""
    _selected_mount_shape_id: str = ""
    _selected_mount_consumer_id: str = ""
    _debug_target_url: str = ""
    _debug_private_network_id: str = ""
    _last_debug_probe: SmokeTestResult | None = None

    def __post_init__(self) -> None:
        if not self._selected_model_id:
            enabled_models = self.harness.client.worker_bridge.config.enabled_models
            self._selected_model_id = enabled_models[0] if enabled_models else ""
        if not self._debug_target_url:
            self._debug_target_url = self.harness.lan_platform_url or self.harness.modulo_url
        if not self._debug_private_network_id:
            self._debug_private_network_id = (
                self.harness.client.worker_bridge.config.private_network_id or ""
            )
        self._sync_debug_target_into_session_bridge()

    def refresh(self) -> GuiShellState:
        return self._build_state(
            status=self.harness.client.get_status(),
            onboarding=self.harness.client.get_onboarding_status(),
        )

    def configure_openclaw(self) -> GuiShellState:
        self.harness.client.stage_openclaw_connection()
        return self.refresh()

    def apply_openclaw_connection(self) -> GuiShellState:
        self.harness.client.apply_openclaw_connection_plan()
        return self.refresh()

    def select_hosting_model(self, model_id: str) -> GuiShellState:
        self._selected_model_id = model_id
        self.harness.client.set_hosting_model(model_id)
        return self.refresh()

    def select_use_model(self, model_id: str) -> GuiShellState:
        self._selected_use_model_id = model_id
        return self.refresh()

    def select_mount_shape(self, shape_id: str) -> GuiShellState:
        self._selected_mount_shape_id = shape_id
        self._selected_mount_consumer_id = ""
        return self.refresh()

    def select_mount_consumer(self, consumer_id: str) -> GuiShellState:
        self._selected_mount_consumer_id = consumer_id
        return self.refresh()

    def start_hosting(self) -> GuiShellState:
        self.harness.client.start_hosting()
        return self.refresh()

    def stop_hosting(self) -> GuiShellState:
        self.harness.client.stop_hosting()
        return self.refresh()

    def restart_hosting(self) -> GuiShellState:
        self.harness.client.restart_hosting()
        return self.refresh()

    def poll_worker(self) -> GuiShellState:
        if self.harness.client.get_status().hosting_enabled:
            self.harness.client.run_hosting_cycle()
        return self.refresh()

    def run_smoke_test(self) -> GuiShellState:
        self._last_smoke_test_prompt = "Constrained GUI smoke probe"
        self.harness.client.run_smoke_test(
            GUI_SMOKE_TEST_USER_PROMPT,
            system_message=GUI_SMOKE_TEST_SYSTEM_PROMPT,
        )
        return self.refresh()

    def set_debug_target_url(self, url: str) -> GuiShellState:
        self._debug_target_url = url.strip()
        self.harness.set_platform_target_url(self._debug_target_url or self.harness.modulo_url)
        return self.refresh()

    def set_debug_private_network_id(self, private_network_id: str) -> GuiShellState:
        self._debug_private_network_id = private_network_id.strip()
        return self.refresh()

    def run_debug_probe(self) -> GuiShellState:
        self._last_debug_probe = self.harness.run_debug_platform_probe(
            platform_url=self._debug_target_url or self.harness.modulo_url,
            private_network_id=self._debug_private_network_id,
            model_id=self._debug_model_id(self.harness.client.get_status()),
        )
        return self.refresh()

    @staticmethod
    def build_default(*, platform_target_url: str = "") -> "GuiAppController":
        return GuiAppController(
            harness=LocalPrototypeHarness(),
            _debug_target_url=platform_target_url.strip(),
        )

    def _build_state(self, *, status: ClientStatus, onboarding: OnboardingStatus) -> GuiShellState:
        worker = status.worker
        smoke_test = status.smoke_test
        use_available_model_ids, use_available_model_labels = self._use_model_options(status)
        if not self._selected_use_model_id or self._selected_use_model_id not in use_available_model_ids:
            self._selected_use_model_id = self._initial_use_model_id(
                status=status,
                available_model_ids=use_available_model_ids,
            )
        (
            use_selected_model_label,
            use_selected_model_source,
        ) = self._selected_use_presentation(
            status=status,
            selected_use_model_id=self._selected_use_model_id,
        )
        mount_shape_ids, mount_shape_labels = self._mount_shape_options()
        if self._selected_mount_shape_id not in mount_shape_ids:
            self._selected_mount_shape_id = ""
        mount_selected_shape_label = self._mount_shape_label(self._selected_mount_shape_id)
        mount_consumer_ids, mount_consumer_labels = self._mount_consumer_options(
            status=status,
            shape_id=self._selected_mount_shape_id,
        )
        if self._selected_mount_consumer_id not in mount_consumer_ids:
            self._selected_mount_consumer_id = ""

        return GuiShellState(
            connected_to_modulo=onboarding.connected_to_modulo,
            openclaw_configured=onboarding.openclaw_configured,
            hosting_enabled=onboarding.hosting_enabled,
            worker_registered=onboarding.worker_registered,
            worker_healthy=onboarding.worker_healthy,
            home_title="Modulo",
            home_subtitle=self._home_subtitle(onboarding),
            connection_summary=self._connection_summary(onboarding),
            hosting_summary=self._hosting_summary(onboarding),
            smoke_status_badge="PASS" if onboarding.smoke_test_ok else "PENDING",
            worker_status_badge="HEALTHY" if onboarding.worker_healthy else "UNHEALTHY",
            primary_action_label="Configure OpenClaw" if not onboarding.openclaw_configured else "Run Smoke Test",
            secondary_action_label="Enable Hosting" if not onboarding.hosting_enabled else "Disable Hosting",
            connect_action_enabled=True,
            openclaw_action_label=(
                "Review OpenClaw Setup" if status.openclaw.configured else "Configure OpenClaw"
            ),
            openclaw_status_badge=self._openclaw_status_badge(status),
            openclaw_summary=status.openclaw.summary,
            openclaw_details=status.openclaw.details,
            openclaw_safety_note=status.openclaw.safety_note,
            openclaw_guidance_badge=self._openclaw_guidance_badge(status),
            openclaw_guidance_summary=self._openclaw_guidance_summary(status),
            openclaw_next_steps=self._openclaw_next_steps(status),
            openclaw_plan_summary=status.openclaw.connection_plan.summary,
            openclaw_plan_details=status.openclaw.connection_plan.details,
            openclaw_plan_changes=status.openclaw.connection_plan.change_lines,
            openclaw_plan_apply_enabled=status.openclaw.connection_plan.apply_ready,
            openclaw_plan_apply_label=status.openclaw.connection_plan.apply_label,
            buyer_platform_summary=status.platform.buyer_routing_summary,
            buyer_account_summary=status.platform.account_summary,
            buyer_network_models=self._buyer_model_lines(status, source="network"),
            buyer_cloud_models=self._buyer_model_lines(status, source="cloud"),
            buyer_credits_summary=status.platform.credits_summary,
            buyer_config_summary=status.platform.buyer_config_summary,
            use_status_badge=self._use_status_badge(status),
            use_summary=self._use_summary(status),
            use_selected_model_id=self._selected_use_model_id,
            use_available_model_ids=use_available_model_ids,
            use_available_model_labels=use_available_model_labels,
            use_selected_model_label=use_selected_model_label,
            use_selected_model_source=use_selected_model_source,
            use_route_target=status.use.route.active_route_target,
            use_provider_label=status.use.route.active_provider or "Unknown",
            use_route_health_value=self._use_route_health_value(status),
            use_route_health_summary=self._use_route_health_summary(status),
            mount_selected_shape_id=self._selected_mount_shape_id,
            mount_available_shape_ids=mount_shape_ids,
            mount_available_shape_labels=mount_shape_labels,
            mount_selected_shape_label=mount_selected_shape_label,
            mount_selected_consumer_id=self._selected_mount_consumer_id,
            mount_available_consumer_ids=mount_consumer_ids,
            mount_available_consumer_labels=mount_consumer_labels,
            use_mount_status_value=self._use_mount_status_value(status),
            use_mount_status_summary=self._use_mount_status_summary(status),
            mount_consumer_label=self._mount_consumer_label(status),
            mount_consumer_summary=self._mount_consumer_summary(status),
            mount_detail_lines=self._mount_detail_lines(status),
            use_route_details=self._use_route_details(status),
            use_local_model_lines=self._use_local_model_lines(status),
            use_private_model_lines=self._use_scope_model_lines(status, scope_id="private"),
            use_public_model_lines=self._use_scope_model_lines(status, scope_id="public"),
            hosting_selected_model_id=status.hosting_setup.selected_model_id,
            hosting_available_model_ids=status.hosting_setup.available_model_ids,
            hosting_available_model_labels=status.hosting_setup.available_model_labels,
            hosting_supported_installed_model_ids=status.hosting_setup.supported_installed_model_ids,
            hosting_supported_missing_model_ids=status.hosting_setup.supported_missing_model_ids,
            hosting_unsupported_installed_model_ids=status.hosting_setup.unsupported_installed_model_ids,
            hosting_mode_badge=self._hosting_mode_badge(status),
            hosting_warm_state_badge=status.hosting_setup.warm_state_badge,
            hosting_warm_summary=status.hosting_setup.warm_summary,
            hosting_warm_details=status.hosting_setup.warm_details,
            ollama_status_badge=(
                "AVAILABLE" if status.hosting_setup.ollama_available else "UNAVAILABLE"
            ),
            ollama_summary=self._ollama_summary(status),
            ollama_inventory_summary=self._ollama_inventory_summary(status),
            hosting_readiness_badge=(
                "READY" if status.hosting_setup.preflight.ok else "BLOCKED"
            ),
            hosting_preflight_summary=status.hosting_setup.preflight.summary,
            hosting_preflight_reason=status.hosting_setup.preflight.failure_reason,
            hosting_preflight_checks=self._hosting_preflight_checks(status),
            hosting_setup_summary=status.hosting_setup.readiness_summary,
            hosting_setup_details=status.hosting_setup.readiness_details,
            hosting_setup_action_enabled=bool(status.hosting_setup.available_model_ids),
            execution_mode_badge=self._execution_mode_badge(status, smoke_test),
            execution_summary=self._execution_summary(status, smoke_test),
            start_action_enabled=(not onboarding.hosting_enabled and status.hosting_setup.can_enable_hosting),
            stop_action_enabled=onboarding.hosting_enabled,
            restart_action_enabled=onboarding.hosting_enabled,
            smoke_action_enabled=onboarding.connected_to_modulo,
            worker_registration_text=self._worker_registration_text(onboarding),
            worker_health_summary=self._worker_health_summary(onboarding),
            worker_activity_summary=self._worker_activity_summary(worker),
            worker_id=worker.worker_id if worker else "",
            worker_runtime_state=worker.runtime_state.value if worker else WorkerRuntimeState.STOPPED.value,
            enabled_models_text=", ".join(worker.enabled_models) if worker and worker.enabled_models else "",
            current_load=worker.current_load if worker else 0,
            completed_jobs=worker.completed_jobs if worker else 0,
            failed_jobs=worker.failed_jobs if worker else 0,
            last_job_id=worker.last_job_id if worker else "",
            last_job_status=worker.last_job_status.value if worker and worker.last_job_status else "",
            last_worker_error=onboarding.last_worker_error,
            smoke_test_ok=onboarding.smoke_test_ok,
            smoke_test_prompt=self._last_smoke_test_prompt,
            smoke_test_summary=self._smoke_test_summary(smoke_test),
            smoke_test_details=self._smoke_test_details(smoke_test),
            smoke_test_result_label=self._smoke_test_result_label(smoke_test),
            diagnostics_summary=self._diagnostics_summary(onboarding, smoke_test),
            diagnostics_details=self._diagnostics_details(onboarding, smoke_test),
            route_trace_result_label=self._route_trace_result_label(status),
            route_trace_summary=self._route_trace_summary(status),
            route_trace_details=self._route_trace_details(status),
            continuity_summary=status.activity.continuity_summary,
            activity_lines=self._activity_lines(status),
            debug_status_badge=self._debug_status_badge(status),
            debug_summary=self._debug_summary(status),
            debug_platform_url=self.harness.modulo_url,
            debug_target_url=self._debug_target_url or self.harness.modulo_url,
            debug_lan_platform_url=self.harness.lan_platform_url,
            debug_private_network_id=self._debug_private_network_id,
            debug_worker_id=self.harness.client.worker_bridge.config.worker_id,
            debug_model_id=self._debug_model_id(status),
            debug_topology_lines=self._debug_topology_lines(status),
            debug_worker_command=self._debug_worker_command(status),
            debug_request_command=self._debug_request_command(status),
            debug_probe_result_label=self._debug_probe_result_label(),
            debug_probe_summary=self._debug_probe_summary(),
            debug_probe_details=self._debug_probe_details(),
        )

    @staticmethod
    def _smoke_test_summary(smoke_test: SmokeTestResult | None) -> str:
        if smoke_test is None:
            return "No smoke test run yet."
        mode_suffix = (
            f" via {smoke_test.execution_mode.upper()} execution"
            if smoke_test.execution_mode
            else ""
        )
        if smoke_test.ok:
            return f"Smoke test passed on {smoke_test.model_id or 'unknown model'}{mode_suffix}."
        return f"Smoke test failed{mode_suffix}: {smoke_test.error or 'unknown error'}"

    @staticmethod
    def _smoke_test_details(smoke_test: SmokeTestResult | None) -> str:
        if smoke_test is None:
            return ""
        lines = ["Probe: Constrained GUI smoke probe"]
        if smoke_test.execution_mode:
            lines.append(f"Execution mode: {smoke_test.execution_mode.upper()}")
        if smoke_test.execution_summary:
            lines.append(f"Execution summary: {smoke_test.execution_summary}")
        if smoke_test.ok:
            lines.append(f"Response: {smoke_test.response_text}")
            return "\n".join(lines)
        lines.append(f"Error: {smoke_test.error}")
        return "\n".join(lines)

    @staticmethod
    def _smoke_test_result_label(smoke_test: SmokeTestResult | None) -> str:
        if smoke_test is None:
            return "Not run yet"
        return "Pass" if smoke_test.ok else "Fail"

    @staticmethod
    def _use_status_badge(status: ClientStatus) -> str:
        if status.use.route.active_route_target == "OpenClaw":
            return "Use: Ready"
        if status.use.route.active_route_target == "OpenClaw (staged)":
            return "Use: Configure"
        return "Use: Setup"

    @staticmethod
    def _use_summary(status: ClientStatus) -> str:
        return status.use.summary

    def _use_route_health_value(self, status: ClientStatus) -> str:
        if status.openclaw.configured and self._selected_mount_shape_id == "openai_api":
            return "Ready"
        return "Not ready"

    def _use_route_health_summary(self, status: ClientStatus) -> str:
        if status.openclaw.configured and self._selected_mount_shape_id == "openai_api":
            return "The selected shape and consumer are configured, so this client is ready to hand requests off through that edge."
        if not self._selected_mount_shape_id:
            return "Step 1: choose a shape so Modulo knows what kind of endpoint to expose."
        if not self._selected_mount_consumer_id:
            return "Step 2: choose a compatible consumer. Modulo will stage the best setup it can, then wait for your confirmation before it applies real edge changes."
        if self._selected_mount_shape_id == "openai_api" and status.openclaw.connection_plan.apply_ready:
            return "The selected edge is staged, but Modulo is still waiting for your confirmation before it applies those changes."
        if not status.platform.connected:
            return "The selected route still needs a reachable platform target before shared execution can be trusted."
        return "The shape and consumer are selected, but the edge still needs attention before it is fully ready."

    def _use_route_reason(self, status: ClientStatus) -> str:
        if status.openclaw.configured and self._selected_mount_shape_id == "openai_api":
            return "Ready to use through OpenClaw."
        if not self._selected_mount_shape_id:
            return "Choose a shape."
        if not self._selected_mount_consumer_id:
            return "Choose a consumer."
        if self._selected_mount_shape_id == "openai_api" and status.openclaw.connection_plan.apply_ready:
            return "Confirm the staged setup."
        if not status.platform.connected:
            return "Reconnect the platform target."
        return "Finish the edge setup."

    def _use_mount_status_value(self, status: ClientStatus) -> str:
        if not self._selected_mount_shape_id:
            return "Choose shape"
        if not self._selected_mount_consumer_id:
            return "Choose consumer"
        if self._selected_mount_consumer_id == "openclaw" and status.openclaw.configured:
            return "Ready"
        if self._selected_mount_consumer_id == "openclaw" and status.openclaw.connection_plan.apply_ready:
            return "Staged"
        if self._selected_mount_consumer_id:
            return "Shape selected"
        return "Not configured"

    def _use_mount_status_summary(self, status: ClientStatus) -> str:
        if not self._selected_mount_shape_id:
            return "Choose a shape first. Modulo will keep the setup lightweight until you decide what kind of endpoint to expose."
        if not self._selected_mount_consumer_id:
            return "Choose a compatible consumer next. Modulo will stage the best setup it can, then wait for your confirmation before it changes anything at the edge."
        if self._selected_mount_consumer_id == "openclaw" and status.openclaw.configured:
            return "OpenClaw is configured for the selected shape."
        if self._selected_mount_consumer_id == "openclaw" and status.openclaw.connection_plan.apply_ready:
            return "OpenClaw is selected and the edge plan is ready for your confirmation."
        if self._selected_mount_consumer_id == "openclaw" and status.openclaw.installed:
            return "OpenClaw is selected. Modulo can prepare the edge wiring, but it will still ask before making the real changes."
        if self._selected_mount_shape_id == "ollama":
            return "Ollama shape is selected. Choose a compatible consumer to continue."
        if self._selected_mount_shape_id == "modulo_native":
            return "Modulo Native is selected. A compatible consumer will surface here when available."
        return "No mounted edge is configured yet."

    @staticmethod
    def _mount_shape_options() -> tuple[tuple[str, ...], tuple[str, ...]]:
        return (
            ("", "openai_api", "ollama", "modulo_native"),
            ("Choose shape...", "OpenAI API", "Ollama", "Modulo Native"),
        )

    @staticmethod
    def _mount_shape_label(shape_id: str) -> str:
        return {
            "openai_api": "OpenAI API",
            "ollama": "Ollama",
            "modulo_native": "Modulo Native",
        }.get(shape_id, "Not selected")

    @staticmethod
    def _mount_consumer_options(
        status: ClientStatus,
        *,
        shape_id: str,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        del status
        if not shape_id:
            return (("",), ("Choose consumer...",))
        if shape_id in {"openai_api", "ollama"}:
            return (("", "openclaw"), ("Choose consumer...", "OpenClaw"))
        return (("",), ("Choose consumer...",))

    def _mount_consumer_label(self, status: ClientStatus) -> str:
        if self._selected_mount_consumer_id == "openclaw":
            return "OpenClaw"
        if self._selected_mount_shape_id:
            return "Not configured"
        return "Not selected"

    def _mount_consumer_summary(self, status: ClientStatus) -> str:
        if not self._selected_mount_shape_id:
            return "Select a shape first. Modulo will keep the next step light until you choose how the endpoint should look."
        if not self._selected_mount_consumer_id:
            return "Pick a compatible consumer next. Modulo will prepare the best setup it can, then wait for your confirmation before it changes anything at the edge."
        if self._selected_mount_consumer_id == "openclaw":
            if status.openclaw.configured:
                return "OpenClaw is selected for this shape and the current edge already looks configured."
            if status.openclaw.connection_plan.apply_ready:
                return "OpenClaw is selected. Modulo has prepared a staged plan and is waiting for your confirmation before it applies it."
            if status.openclaw.installed:
                return "OpenClaw is selected. Modulo can stage a best-effort setup, then ask before making the real edge changes."
            return "OpenClaw is selected, but it is not installed yet."
        if self._selected_mount_shape_id == "ollama":
            return "This shape will eventually expose more Ollama-compatible consumers."
        return "This shape will eventually expose Modulo-native consumers without provider-specific wrapping."

    def _mount_detail_lines(self, status: ClientStatus) -> tuple[str, ...]:
        if not self._selected_mount_shape_id:
            return (
                "Step 1: Choose a shape.",
                "Shape tells Modulo what kind of endpoint you want to expose.",
            )
        if not self._selected_mount_consumer_id:
            return (
                "Step 2: Choose a consumer.",
                "Modulo only shows compatible consumers for the selected shape.",
                "When you pick one, Modulo will stage the best setup it can and wait for confirmation before applying real edge changes.",
            )
        if self._selected_mount_consumer_id == "openclaw":
            details = [
                "Step 3: Review the proposed edge setup.",
                f"OpenClaw: {status.openclaw.summary}",
                f"Next: {self._openclaw_guidance_summary(status)}",
            ]
            if status.openclaw.connection_plan.summary:
                details.append(f"Plan: {status.openclaw.connection_plan.summary}")
            return tuple(line for line in details if line)
        if self._selected_mount_shape_id == "ollama":
            return (
                "Ollama shape is selected.",
                "No consumer-specific setup lives here yet.",
            )
        return (
            "Modulo Native shape is selected.",
            "Direct native consumer setup has not been surfaced yet.",
        )

    @staticmethod
    def _home_subtitle(onboarding: OnboardingStatus) -> str:
        return "Use, hosting, and diagnostics are managed separately in this client."

    @staticmethod
    def _connection_summary(onboarding: OnboardingStatus) -> str:
        return (
            "OpenClaw routing is configured in Modulo."
            if onboarding.openclaw_configured
            else "OpenClaw is not configured yet. Review the staged plan before applying it."
        )

    @staticmethod
    def _hosting_summary(onboarding: OnboardingStatus) -> str:
        if onboarding.hosting_enabled and onboarding.worker_healthy:
            return "Hosting is enabled and the worker is healthy."
        if onboarding.hosting_enabled:
            return "Hosting is enabled, but the worker needs attention."
        return "Hosting is disabled."

    @staticmethod
    def _worker_registration_text(onboarding: OnboardingStatus) -> str:
        return (
            "Registered with the Modulo cloud."
            if onboarding.worker_registered
            else "Not registered with the Modulo cloud yet."
        )

    @staticmethod
    def _worker_health_summary(onboarding: OnboardingStatus) -> str:
        if onboarding.worker_healthy:
            return "Worker health looks good."
        if onboarding.hosting_enabled:
            return "Worker needs attention before hosting feels reliable."
        return "Worker is idle because hosting is disabled."

    @staticmethod
    def _worker_activity_summary(worker: WorkerStatusSnapshot | None) -> str:
        if worker is None:
            return "No worker activity yet."
        if worker.last_job_id and worker.last_job_status:
            return (
                f"Last job {worker.last_job_id} finished with status "
                f"{worker.last_job_status.value}."
            )
        if worker.completed_jobs or worker.failed_jobs:
            return (
                f"{worker.completed_jobs} completed jobs and "
                f"{worker.failed_jobs} failed jobs so far."
            )
        return "Worker is ready but has not processed a job yet."

    @staticmethod
    def _diagnostics_summary(
        onboarding: OnboardingStatus,
        smoke_test: SmokeTestResult | None,
    ) -> str:
        if smoke_test is None:
            return "Run a smoke test to capture an end-to-end confidence check."
        if smoke_test.ok:
            return "Smoke test passed and the latest diagnostics look healthy."
        if onboarding.last_worker_error:
            return "Smoke test failed and the worker reported an error."
        return "Smoke test failed before the worker produced a healthy result."

    @staticmethod
    def _diagnostics_details(
        onboarding: OnboardingStatus,
        smoke_test: SmokeTestResult | None,
    ) -> str:
        lines = [
            f"Smoke test result: {GuiAppController._smoke_test_result_label(smoke_test)}",
            f"Last worker error: {onboarding.last_worker_error or 'None'}",
        ]
        if smoke_test is not None:
            lines.append("Probe: Constrained GUI smoke probe")
            if smoke_test.execution_mode:
                lines.append(f"Execution mode: {smoke_test.execution_mode.upper()}")
            if smoke_test.execution_summary:
                lines.append(f"Execution summary: {smoke_test.execution_summary}")
            if smoke_test.ok:
                lines.append(f"Response: {smoke_test.response_text}")
            else:
                lines.append(f"Smoke test error: {smoke_test.error or 'Unknown error'}")
        return "\n".join(lines)

    @staticmethod
    def _route_trace_result_label(status: ClientStatus) -> str:
        trace = status.latest_route_trace
        if not trace.available:
            return "Not captured"
        if trace.final_status == "completed":
            return "Completed"
        if trace.final_status in {"failed", "error"}:
            return "Needs attention"
        if trace.final_status == "no_route":
            return "No route found"
        if trace.final_status:
            return trace.final_status.replace("_", " ").title()
        return "Captured"

    @classmethod
    def _route_trace_summary(cls, status: ClientStatus) -> str:
        trace = status.latest_route_trace
        if not trace.available:
            return trace.summary

        source = cls._route_trace_source_label(trace.source)
        scope = cls._route_trace_scope_label(trace.scope)
        if trace.final_status == "completed":
            worker = trace.selected_worker_id or "an available worker"
            return f"Latest request routed through {source} in {scope} scope to {worker} and completed successfully."
        if trace.selected_worker_id:
            return (
                f"Latest request routed through {source} in {scope} scope to "
                f"{trace.selected_worker_id}, but it ended with {cls._route_trace_outcome_label(trace.final_status).lower()}."
            )
        if trace.route_reason:
            return f"Latest request could not complete in {scope} scope. {trace.route_reason}"
        return f"Latest request did not find an eligible route in {scope} scope."

    @classmethod
    def _route_trace_details(cls, status: ClientStatus) -> str:
        trace = status.latest_route_trace
        if not trace.available:
            return trace.details

        lines = [
            f"Model: {trace.model_id or 'Unknown'}",
            f"Source: {cls._route_trace_source_label(trace.source)}",
            f"Scope: {cls._route_trace_scope_label(trace.scope)}",
        ]
        if trace.private_network_id:
            lines.append(f"Private network: {trace.private_network_id}")
        lines.append(f"Outcome: {cls._route_trace_outcome_label(trace.final_status)}")
        lines.append(
            f"Worker: {trace.selected_worker_id or 'No worker selected'}"
            + (
                f" ({cls._route_trace_worker_kind_label(trace.selected_worker_kind)})"
                if trace.selected_worker_kind
                else ""
            )
        )
        if trace.route_reason or trace.route_reason_code:
            lines.append(
                f"Why this route: {trace.route_reason or cls._route_trace_reason_label(trace.route_reason_code)}"
            )
        if trace.attempt_number or trace.retry_count:
            total_attempts = max(trace.attempt_number, trace.retry_count + 1)
            lines.append(f"Attempts: {total_attempts} total ({trace.retry_count} retr{'y' if trace.retry_count == 1 else 'ies'})")
        if trace.continuity_used:
            lines.append("Continuity: reused a recent worker path")
        if trace.warm_path_used:
            lines.append("Warm path: preferred a worker that was already warm")
        if trace.final_error:
            lines.append(f"Error: {trace.final_error}")
        if trace.filtered_workers:
            lines.append("")
            lines.append("Filtered workers:")
            for item in trace.filtered_workers:
                detail = f" - {item.worker_id}: {cls._route_trace_filtered_reason_label(item.reason_code)}"
                if item.detail:
                    detail = f"{detail} ({item.detail})"
                lines.append(detail)
        return "\n".join(lines)

    @staticmethod
    def _route_trace_source_label(source: str) -> str:
        return {
            "local": "Local",
            "network": "Private",
            "public": "Public",
            "cloud": "Cloud",
        }.get(source, source.replace("_", " ").title() if source else "Unknown")

    @staticmethod
    def _route_trace_scope_label(scope: str) -> str:
        return {
            "local": "Local",
            "private": "Private",
            "public": "Public",
            "cloud": "Cloud",
        }.get(scope, scope.replace("_", " ").title() if scope else "Unknown")

    @staticmethod
    def _route_trace_outcome_label(final_status: str) -> str:
        return {
            "completed": "Completed",
            "failed": "Failed",
            "error": "Failed",
            "no_route": "No route found",
            "cancelled": "Cancelled",
        }.get(final_status, final_status.replace("_", " ").title() if final_status else "Captured")

    @staticmethod
    def _route_trace_worker_kind_label(kind: str) -> str:
        return {
            "local": "local host",
            "network": "network host",
            "cloud": "cloud host",
        }.get(kind, kind.replace("_", " ").title() if kind else "worker")

    @staticmethod
    def _route_trace_reason_label(reason_code: str) -> str:
        return {
            "selected_requested_mode": "Selected the best healthy worker for the requested route.",
            "buyer_continuity_lease": "Stayed with a recent worker for continuity.",
            "cloud_fallback_exact_match": "Private routing had no eligible worker, so an exact cloud fallback was chosen.",
            "no_eligible_target": "No eligible execution target was available.",
            "unsupported_model": "The requested model is not supported for this route.",
            "streaming_disabled": "Streaming is disabled for this route.",
            "tool_calling_disabled": "Tool calling is disabled for this route.",
            "healthy_exact_match": "Matched the requested model on a healthy worker.",
        }.get(reason_code, reason_code.replace("_", " ").capitalize() if reason_code else "Unavailable")

    @staticmethod
    def _route_trace_filtered_reason_label(reason_code: str) -> str:
        return {
            "excluded_worker": "skipped because it was explicitly excluded",
            "worker_kind_mismatch": "skipped because it was the wrong worker type",
            "worker_unhealthy": "skipped because it was unhealthy",
            "private_network_mismatch": "skipped because it belonged to a different private network",
            "scope_mismatch": "skipped because its scope did not match",
            "model_not_advertised": "skipped because it did not advertise this model",
            "worker_at_capacity": "skipped because it was already at capacity",
        }.get(reason_code, reason_code.replace("_", " ") if reason_code else "filtered")

    @staticmethod
    def _execution_mode_badge(
        status: ClientStatus,
        smoke_test: SmokeTestResult | None,
    ) -> str:
        if smoke_test is not None and smoke_test.execution_mode:
            return smoke_test.execution_mode.upper()
        return status.hosting_setup.hosting_mode_label.upper()

    @staticmethod
    def _execution_summary(
        status: ClientStatus,
        smoke_test: SmokeTestResult | None,
    ) -> str:
        if smoke_test is not None and smoke_test.execution_summary:
            return smoke_test.execution_summary
        if status.hosting_setup.hosting_mode_label == "prototype":
            return (
                "Current worker path is prototype-safe until the selected model passes "
                "local runtime readiness."
            )
        return "Current worker path is ready for real local execution."

    @staticmethod
    def _hosting_mode_badge(status: ClientStatus) -> str:
        if status.hosting_setup.hosting_mode_label == "prototype":
            return "Prototype"
        return "Ollama"

    @staticmethod
    def _activity_lines(status: ClientStatus) -> tuple[str, ...]:
        if not status.activity.recent_activity:
            return ("No recent activity yet.",)
        lines: list[str] = []
        for entry in status.activity.recent_activity:
            buyer_label = entry.buyer_id or "anonymous request"
            lines.append(
                f"{entry.job_id}: {buyer_label} -> {entry.worker_id} "
                f"[{entry.status}] | {entry.continuity_hint}"
            )
        return tuple(lines)

    @staticmethod
    def _buyer_model_lines(status: ClientStatus, *, source: str) -> tuple[str, ...]:
        if source == "network":
            models = status.platform.private_models or status.platform.network_models
            empty = "No private models available yet."
        else:
            models = status.platform.cloud_models
            empty = "No cloud models available yet."
        if not models:
            return (empty,)
        return tuple(
            f"{model.display_name} [{model.model_id}]"
            + (f" - {model.summary}" if model.summary else "")
            for model in models
        )

    @staticmethod
    def _use_model_options(status: ClientStatus) -> tuple[tuple[str, ...], tuple[str, ...]]:
        option_ids: list[str] = []
        option_labels: list[str] = []
        for scope in status.use.scopes:
            if not scope.models:
                continue
            option_ids.append(GuiAppController._use_scope_header_id(scope.scope_id))
            option_labels.append(scope.display_label)
            for model in scope.models:
                scoped_id = f"{model.source}:{model.model_id}"
                option_ids.append(scoped_id)
                option_labels.append(
                    f"  {GuiAppController._use_source_icon(model.source)} {model.display_name}"
                )
        return tuple(option_ids), tuple(option_labels)

    @staticmethod
    def _use_scope_header_id(scope_id: str) -> str:
        return f"__header__:{scope_id}"

    @staticmethod
    def _is_use_scope_header(option_id: str) -> bool:
        return option_id.startswith("__header__:")

    @staticmethod
    def _initial_use_model_id(
        *,
        status: ClientStatus,
        available_model_ids: tuple[str, ...],
    ) -> str:
        primary = status.openclaw.current_primary_model
        provider = status.openclaw.current_provider
        if primary:
            if "/" in primary:
                provider, model_id = primary.split("/", 1)
            else:
                model_id = primary
            scoped = f"{provider}:{model_id}" if provider else model_id
            if scoped in available_model_ids:
                return scoped
            local_scoped = f"local:{model_id}"
            if local_scoped in available_model_ids:
                return local_scoped
        for option_id in available_model_ids:
            if not GuiAppController._is_use_scope_header(option_id):
                return option_id
        return ""

    @staticmethod
    def _use_selected_model_label(
        selected_use_model_id: str,
        available_model_ids: tuple[str, ...],
        available_model_labels: tuple[str, ...],
    ) -> str:
        if not selected_use_model_id:
            return "No model selected"
        try:
            index = available_model_ids.index(selected_use_model_id)
        except ValueError:
            return selected_use_model_id
        return available_model_labels[index]

    @staticmethod
    def _selected_use_presentation(
        *,
        status: ClientStatus,
        selected_use_model_id: str,
    ) -> tuple[str, str]:
        if not selected_use_model_id:
            return ("No model selected", "Unknown")
        selected_scope_id = GuiAppController._scope_id_from_use_model_id(selected_use_model_id)
        selected_model_key = GuiAppController._model_id_from_use_model_id(selected_use_model_id)
        for scope in status.use.scopes:
            if scope.scope_id != selected_scope_id:
                continue
            for model in scope.models:
                if model.model_id == selected_model_key:
                    return model.display_name, scope.display_label
        return selected_model_key or "No model selected", GuiAppController._use_model_source_label(
            selected_use_model_id
        )

    @staticmethod
    def _scope_id_from_use_model_id(selected_use_model_id: str) -> str:
        if ":" not in selected_use_model_id:
            return selected_use_model_id
        source, _ = selected_use_model_id.split(":", 1)
        return "private" if source == "network" else source

    @staticmethod
    def _model_id_from_use_model_id(selected_use_model_id: str) -> str:
        if ":" not in selected_use_model_id:
            return ""
        _, model_id = selected_use_model_id.split(":", 1)
        return model_id

    @staticmethod
    def _use_model_source_label(selected_use_model_id: str) -> str:
        if selected_use_model_id == "local":
            return "Local"
        if selected_use_model_id == "private":
            return "Private"
        if selected_use_model_id == "public":
            return "Public"
        if selected_use_model_id == "cloud":
            return "Cloud"
        if selected_use_model_id.startswith("local:"):
            return "Local"
        if selected_use_model_id.startswith("private:") or selected_use_model_id.startswith("network:"):
            return "Private"
        if selected_use_model_id.startswith("public:"):
            return "Public"
        if selected_use_model_id.startswith("cloud:"):
            return "Cloud"
        return "Unknown"

    def _use_route_details(self, status: ClientStatus) -> tuple[str, ...]:
        selected_model_label, selected_source_label = self._selected_use_presentation(
            status=status,
            selected_use_model_id=self._selected_use_model_id,
        )
        shape_label = self._mount_shape_label(self._selected_mount_shape_id)
        mount_label = self._mount_consumer_label(status)
        reason = self._use_route_reason(status)

        details = [
            f"Model: {selected_model_label or 'No model selected'}",
            f"Source: {selected_source_label or 'Unknown'}",
            f"Shape: {shape_label}",
            f"Mount: {mount_label}",
            f"Status: {self._use_route_health_value(status)}",
            f"Reason: {reason}",
        ]
        return tuple(line for line in details if line)

    @staticmethod
    def _use_local_model_lines(status: ClientStatus) -> tuple[str, ...]:
        return GuiAppController._use_scope_model_lines(status, scope_id="local")

    @staticmethod
    def _use_scope_model_lines(status: ClientStatus, *, scope_id: str) -> tuple[str, ...]:
        scope = next((item for item in status.use.scopes if item.scope_id == scope_id), None)
        if scope is None:
            return ("Scope is unavailable.",)
        if not scope.models:
            lines = [scope.summary or f"No {scope.display_label.lower()} models available yet."]
            if scope.route_restriction:
                lines.append(scope.route_restriction)
            return tuple(lines)
        return tuple(
            f"{GuiAppController._use_source_icon(model.source)} {model.display_name}"
            + (f" [{model.model_id}]" if model.model_id != model.display_name else "")
            + (f" - {model.summary}" if model.summary else "")
            for model in scope.models
        )

    @staticmethod
    def _use_source_icon(source: str) -> str:
        return {
            "local": "🖥",
            "private": "◎",
            "public": "◌",
            "cloud": "☁",
            "network": "◎",
        }.get(source, "•")

    @staticmethod
    def _openclaw_status_badge(status: ClientStatus) -> str:
        if status.openclaw.configured:
            return "CONFIGURED"
        if status.openclaw.installed:
            return "INSTALLED"
        return "NOT INSTALLED"

    @staticmethod
    def _openclaw_guidance_badge(status: ClientStatus) -> str:
        if status.openclaw.error:
            return "ATTENTION"
        if status.openclaw.configured:
            return "READY"
        if status.openclaw.connection_plan.apply_ready:
            return "READY TO APPLY"
        if status.openclaw.installed:
            return "REVIEW"
        return "SETUP NEEDED"

    @staticmethod
    def _openclaw_guidance_summary(status: ClientStatus) -> str:
        if status.openclaw.error:
            return "Modulo found the OpenClaw config, but it could not parse it cleanly."
        if status.openclaw.configured:
            return "Use routing is staged in Modulo. Review the detected state or continue with setup."
        if status.openclaw.connection_plan.apply_ready:
            return "Review the staged routing plan, then apply it when you are comfortable."
        if status.openclaw.installed:
            return "OpenClaw is present locally. Review the detected state before staging a routing plan."
        return "Install OpenClaw first, then return here to stage the routing connection."

    @staticmethod
    def _openclaw_next_steps(status: ClientStatus) -> tuple[str, ...]:
        if status.openclaw.error:
            return (
                "Fix the config parse/read issue shown below.",
                "Refresh or reopen Modulo after correcting the local OpenClaw config.",
                "Stage the routing plan again once the config reads cleanly.",
            )
        if status.openclaw.configured:
            return (
                "Review the detected provider and base URL for sanity.",
                "Choose a model once that selector is available.",
                "Use Diagnostics to run a smoke test through the current prototype path.",
            )
        if status.openclaw.connection_plan.apply_ready:
            return (
                "Review the planned routing changes below.",
                "Apply the staged plan when you are ready.",
                "Return here afterward to confirm the detected state still looks correct.",
            )
        if status.openclaw.installed:
            return (
                "Review the detected OpenClaw config details below.",
                "Stage a routing plan to preview what Modulo would change.",
                "Do not hand-edit local files unless you intend to bypass the staged flow.",
            )
        return (
            "Install OpenClaw on this machine.",
            "Launch Modulo again so it can rediscover the local install.",
            "Stage the routing plan once OpenClaw is present.",
        )

    @staticmethod
    def _ollama_summary(status: ClientStatus) -> str:
        if status.hosting_setup.ollama_available:
            installed_count = len(status.hosting_setup.installed_model_ids)
            return f"Ollama is available locally with {installed_count} discovered model(s)."
        return "Ollama is not available locally yet."

    @staticmethod
    def _ollama_inventory_summary(status: ClientStatus) -> str:
        supported_count = len(status.hosting_setup.supported_installed_model_ids)
        missing_count = len(status.hosting_setup.supported_missing_model_ids)
        unsupported_count = len(status.hosting_setup.unsupported_installed_model_ids)
        return (
            f"{supported_count} supported model(s) installed, "
            f"{missing_count} supported model(s) missing, "
            f"{unsupported_count} installed model(s) outside the curated catalog."
        )

    @staticmethod
    def _debug_status_badge(status: ClientStatus) -> str:
        if status.worker and status.worker.registered_with_cloud:
            return "DEBUG: LIVE"
        return "DEBUG: READY"

    def _debug_summary(self, status: ClientStatus) -> str:
        model_id = self._debug_model_id(status)
        network_id = self._debug_private_network_id or "unset"
        visibility_target = self._debug_target_url or self.harness.modulo_url
        if status.worker and status.worker.registered_with_cloud:
            return (
                f"Current prototype control plane is reachable at {self.harness.modulo_url} "
                f"with worker {self.harness.client.worker_bridge.config.worker_id} registered for "
                f"{model_id} on private network {network_id}. Visibility target: {visibility_target}."
            )
        return (
            f"Use this tab to point another worker at {self.harness.modulo_url} and send a "
            f"private request for {model_id} under private network {network_id}. "
            f"Buyer-side visibility follows {visibility_target}."
        )

    def _debug_model_id(self, status: ClientStatus) -> str:
        selected_use_model = self._selected_use_model_id
        if selected_use_model.startswith(("local:", "private:", "public:", "cloud:", "network:")):
            return selected_use_model.split(":", 1)[1]
        if status.hosting_setup.selected_model_id:
            return status.hosting_setup.selected_model_id
        enabled_models = self.harness.client.worker_bridge.config.enabled_models
        if enabled_models:
            return enabled_models[0]
        return ""

    def _debug_topology_lines(self, status: ClientStatus) -> tuple[str, ...]:
        worker = status.worker
        lines = [
            f"Local control plane: {self.harness.modulo_url}",
            f"Visibility target: {self._debug_target_url or self.harness.modulo_url}",
        ]
        if self.harness.lan_platform_url:
            lines.append(f"LAN control plane: {self.harness.lan_platform_url}")
        lines.extend(
            (
            f"Worker ID: {self.harness.client.worker_bridge.config.worker_id}",
            f"Private network: {self._debug_private_network_id or 'unset'}",
            f"Advertised model: {self._debug_model_id(status) or 'unset'}",
            f"Worker registered: {'yes' if worker and worker.registered_with_cloud else 'no'}",
            f"Worker state: {worker.runtime_state.value if worker else 'stopped'}",
            )
        )
        return tuple(lines)

    def _debug_worker_command(self, status: ClientStatus) -> str:
        model_id = self._debug_model_id(status) or "MODEL_ID"
        network_id = self._debug_private_network_id or "PRIVATE_NETWORK_ID"
        return (
            "python -m modulo.worker.bridge_runner "
            f"--modulo-url {self._debug_target_url or self.harness.modulo_url} "
            "--worker-id worker-laptop "
            f"--model {model_id} "
            "--scope private "
            f"--private-network-id {network_id}"
        )

    def _debug_request_command(self, status: ClientStatus) -> str:
        model_id = self._debug_model_id(status) or "MODEL_ID"
        network_id = self._debug_private_network_id or "PRIVATE_NETWORK_ID"
        target_url = self._debug_target_url or self.harness.modulo_url
        return (
            "$body = @{\n"
            f"  model = \"{model_id}\"\n"
            "  buyer_id = \"buyer-a\"\n"
            "  scope = \"private\"\n"
            f"  private_network_id = \"{network_id}\"\n"
            "  messages = @(\n"
            "    @{ role = \"user\"; content = \"Say hello from the Modulo debug tab.\" }\n"
            "  )\n"
            "  stream = $false\n"
            "} | ConvertTo-Json -Depth 5\n\n"
            f"Invoke-RestMethod -Method Post -Uri \"{target_url}/api/chat\" "
            "-ContentType \"application/json\" -Body $body"
        )

    def _debug_probe_result_label(self) -> str:
        if self._last_debug_probe is None:
            return "Not run yet"
        return "Pass" if self._last_debug_probe.ok else "Fail"

    def _debug_probe_summary(self) -> str:
        if self._last_debug_probe is None:
            return "No debug network probe has run yet."
        if self._last_debug_probe.ok:
            return (
                f"Debug probe reached {self._debug_target_url or self.harness.modulo_url} "
                f"and returned {self._last_debug_probe.model_id} successfully."
            )
        return (
            f"Debug probe failed against {self._debug_target_url or self.harness.modulo_url}: "
            f"{self._last_debug_probe.error or 'unknown error'}"
        )

    def _debug_probe_details(self) -> str:
        if self._last_debug_probe is None:
            return ""
        lines = []
        if self._last_debug_probe.execution_mode:
            lines.append(f"Execution mode: {self._last_debug_probe.execution_mode.upper()}")
        if self._last_debug_probe.execution_summary:
            lines.append(f"Execution summary: {self._last_debug_probe.execution_summary}")
        if self._last_debug_probe.ok:
            lines.append(f"Response: {self._last_debug_probe.response_text}")
        else:
            lines.append(f"Error: {self._last_debug_probe.error}")
        return "\n".join(lines)

    def _sync_debug_target_into_session_bridge(self) -> None:
        self.harness.set_platform_target_url(self._debug_target_url or self.harness.modulo_url)

    @staticmethod
    def _hosting_preflight_checks(status: ClientStatus) -> tuple[str, ...]:
        if not status.hosting_setup.preflight.checks:
            return ("No hosting preflight checks available yet.",)
        return tuple(
            f"{'PASS' if check.ok else 'FAIL'}: {check.summary}"
            for check in status.hosting_setup.preflight.checks
        )
