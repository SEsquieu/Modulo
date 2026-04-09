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
    hosting_selected_model_id: str = ""
    hosting_available_model_ids: tuple[str, ...] = ()
    hosting_available_model_labels: tuple[str, ...] = ()
    hosting_supported_installed_model_ids: tuple[str, ...] = ()
    hosting_supported_missing_model_ids: tuple[str, ...] = ()
    hosting_unsupported_installed_model_ids: tuple[str, ...] = ()
    hosting_mode_badge: str = "REAL"
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
    continuity_summary: str = ""
    activity_lines: tuple[str, ...] = ()


@dataclass
class GuiAppController:
    harness: LocalPrototypeHarness
    _last_smoke_test_prompt: str = "Constrained GUI smoke probe"
    _selected_model_id: str = ""

    def __post_init__(self) -> None:
        if not self._selected_model_id:
            enabled_models = self.harness.client.worker_bridge.config.enabled_models
            self._selected_model_id = enabled_models[0] if enabled_models else ""

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

    @staticmethod
    def build_default() -> "GuiAppController":
        return GuiAppController(harness=LocalPrototypeHarness())

    def _build_state(self, *, status: ClientStatus, onboarding: OnboardingStatus) -> GuiShellState:
        worker = status.worker
        smoke_test = status.smoke_test

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
            hosting_selected_model_id=status.hosting_setup.selected_model_id,
            hosting_available_model_ids=status.hosting_setup.available_model_ids,
            hosting_available_model_labels=status.hosting_setup.available_model_labels,
            hosting_supported_installed_model_ids=status.hosting_setup.supported_installed_model_ids,
            hosting_supported_missing_model_ids=status.hosting_setup.supported_missing_model_ids,
            hosting_unsupported_installed_model_ids=status.hosting_setup.unsupported_installed_model_ids,
            hosting_mode_badge=status.hosting_setup.hosting_mode_label.upper(),
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
            continuity_summary=status.activity.continuity_summary,
            activity_lines=self._activity_lines(status),
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
    def _home_subtitle(onboarding: OnboardingStatus) -> str:
        if onboarding.hosting_enabled:
            return "Use the Host, Buyer, and Diagnostics tabs to manage each side of Modulo separately."
        return "Host, buyer routing, and diagnostics are managed separately in this client."

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
            return "Run a smoke test to capture a buyer-to-worker confidence check."
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
    def _activity_lines(status: ClientStatus) -> tuple[str, ...]:
        if not status.activity.recent_activity:
            return ("No recent buyer activity yet.",)
        lines: list[str] = []
        for entry in status.activity.recent_activity:
            buyer_label = entry.buyer_id or "anonymous buyer"
            lines.append(
                f"{entry.job_id}: {buyer_label} -> {entry.worker_id} "
                f"[{entry.status}] | {entry.continuity_hint}"
            )
        return tuple(lines)

    @staticmethod
    def _buyer_model_lines(status: ClientStatus, *, source: str) -> tuple[str, ...]:
        models = status.platform.network_models if source == "network" else status.platform.cloud_models
        if not models:
            label = "network" if source == "network" else "cloud"
            return (f"No {label} models available yet.",)
        return tuple(
            f"{model.display_name} [{model.model_id}]"
            + (f" - {model.summary}" if model.summary else "")
            for model in models
        )

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
            return "Buyer routing is staged in Modulo. Review the detected state or continue with buyer setup."
        if status.openclaw.connection_plan.apply_ready:
            return "Review the staged buyer-routing plan, then apply it when you are comfortable."
        if status.openclaw.installed:
            return "OpenClaw is present locally. Review the detected state before staging a routing plan."
        return "Install OpenClaw first, then return here to stage the buyer-routing connection."

    @staticmethod
    def _openclaw_next_steps(status: ClientStatus) -> tuple[str, ...]:
        if status.openclaw.error:
            return (
                "Fix the config parse/read issue shown below.",
                "Refresh or reopen Modulo after correcting the local OpenClaw config.",
                "Stage the buyer-routing plan again once the config reads cleanly.",
            )
        if status.openclaw.configured:
            return (
                "Review the detected provider and base URL for sanity.",
                "Choose a buyer model once that selector is available.",
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
                "Stage a buyer-routing plan to preview what Modulo would change.",
                "Do not hand-edit local files unless you intend to bypass the staged flow.",
            )
        return (
            "Install OpenClaw on this machine.",
            "Launch Modulo again so it can rediscover the local install.",
            "Stage the buyer-routing plan once OpenClaw is present.",
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
    def _hosting_preflight_checks(status: ClientStatus) -> tuple[str, ...]:
        if not status.hosting_setup.preflight.checks:
            return ("No hosting preflight checks available yet.",)
        return tuple(
            f"{'PASS' if check.ok else 'FAIL'}: {check.summary}"
            for check in status.hosting_setup.preflight.checks
        )
