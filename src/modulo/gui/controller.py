from __future__ import annotations

from dataclasses import dataclass

from modulo.client.app import ClientStatus, ModuloClientSupervisor, OnboardingStatus, SmokeTestResult
from modulo.common.contracts import WorkerRuntimeState, WorkerStatusSnapshot
from modulo.prototype import LocalPrototypeHarness


@dataclass(frozen=True)
class GuiShellState:
    connected_to_modulo: bool
    openclaw_connected: bool
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
    openclaw_action_label: str = "Connect OpenClaw"
    openclaw_status_badge: str = "NOT CONNECTED"
    openclaw_summary: str = ""
    openclaw_details: str = ""
    openclaw_safety_note: str = ""
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
    smoke_test_prompt: str = "GUI smoke test request"
    smoke_test_summary: str = "No smoke test run yet."
    smoke_test_details: str = ""
    smoke_test_result_label: str = "Not run yet"
    diagnostics_summary: str = ""
    diagnostics_details: str = ""


@dataclass
class GuiAppController:
    harness: LocalPrototypeHarness
    _last_smoke_test_prompt: str = "GUI smoke test request"

    def refresh(self) -> GuiShellState:
        return self._build_state(
            status=self.harness.client.get_status(),
            onboarding=self.harness.client.get_onboarding_status(),
        )

    def connect_openclaw(self) -> GuiShellState:
        self.harness.client.connect_openclaw()
        return self.refresh()

    def disconnect_openclaw(self) -> GuiShellState:
        self.harness.client.disconnect_openclaw()
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

    def run_smoke_test(self, user_message: str = "GUI smoke test request") -> GuiShellState:
        self._last_smoke_test_prompt = user_message
        self.harness.client.run_smoke_test(user_message)
        return self.refresh()

    @staticmethod
    def build_default() -> "GuiAppController":
        return GuiAppController(harness=LocalPrototypeHarness())

    def _build_state(self, *, status: ClientStatus, onboarding: OnboardingStatus) -> GuiShellState:
        worker = status.worker
        smoke_test = status.smoke_test

        return GuiShellState(
            connected_to_modulo=onboarding.connected_to_modulo,
            openclaw_connected=onboarding.openclaw_connected,
            hosting_enabled=onboarding.hosting_enabled,
            worker_registered=onboarding.worker_registered,
            worker_healthy=onboarding.worker_healthy,
            home_title="Modulo",
            home_subtitle=self._home_subtitle(onboarding),
            connection_summary=self._connection_summary(onboarding),
            hosting_summary=self._hosting_summary(onboarding),
            smoke_status_badge="PASS" if onboarding.smoke_test_ok else "PENDING",
            worker_status_badge="HEALTHY" if onboarding.worker_healthy else "UNHEALTHY",
            primary_action_label="Connect OpenClaw" if not onboarding.openclaw_connected else "Run Smoke Test",
            secondary_action_label="Enable Hosting" if not onboarding.hosting_enabled else "Disable Hosting",
            connect_action_enabled=True,
            openclaw_action_label=(
                "Disconnect OpenClaw" if status.openclaw.connected else "Connect OpenClaw"
            ),
            openclaw_status_badge=(
                "CONNECTED" if status.openclaw.connected else "NOT CONNECTED"
            ),
            openclaw_summary=status.openclaw.summary,
            openclaw_details=status.openclaw.details,
            openclaw_safety_note=status.openclaw.safety_note,
            start_action_enabled=not onboarding.hosting_enabled,
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
        )

    @staticmethod
    def _smoke_test_summary(smoke_test: SmokeTestResult | None) -> str:
        if smoke_test is None:
            return "No smoke test run yet."
        if smoke_test.ok:
            return f"Smoke test passed on {smoke_test.model_id or 'unknown model'}."
        return f"Smoke test failed: {smoke_test.error or 'unknown error'}"

    @staticmethod
    def _smoke_test_details(smoke_test: SmokeTestResult | None) -> str:
        if smoke_test is None:
            return ""
        if smoke_test.ok:
            return (
                f"Prompt: {smoke_test.user_message}\n"
                f"Response: {smoke_test.response_text}"
            )
        return f"Prompt: {smoke_test.user_message}\nError: {smoke_test.error}"

    @staticmethod
    def _smoke_test_result_label(smoke_test: SmokeTestResult | None) -> str:
        if smoke_test is None:
            return "Not run yet"
        return "Pass" if smoke_test.ok else "Fail"

    @staticmethod
    def _home_subtitle(onboarding: OnboardingStatus) -> str:
        if onboarding.openclaw_connected and onboarding.hosting_enabled:
            return "Buyer and hosting paths are both active."
        if onboarding.openclaw_connected:
            return "Buyer path is active. Hosting can be enabled when you are ready."
        if onboarding.hosting_enabled:
            return "Hosting is active. OpenClaw is not connected yet."
        return "Connect OpenClaw or enable hosting to begin using Modulo."

    @staticmethod
    def _connection_summary(onboarding: OnboardingStatus) -> str:
        return (
            "OpenClaw buyer path is connected in Modulo."
            if onboarding.openclaw_connected
            else "OpenClaw is not connected yet."
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
            lines.append(f"Prompt: {smoke_test.user_message}")
            if smoke_test.ok:
                lines.append(f"Response: {smoke_test.response_text}")
            else:
                lines.append(f"Smoke test error: {smoke_test.error or 'Unknown error'}")
        return "\n".join(lines)
