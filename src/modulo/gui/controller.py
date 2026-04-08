from __future__ import annotations

from dataclasses import dataclass

from modulo.client.app import ClientStatus, ModuloClientSupervisor, OnboardingStatus, SmokeTestResult
from modulo.common.contracts import WorkerRuntimeState
from modulo.prototype import LocalPrototypeHarness


@dataclass(frozen=True)
class GuiShellState:
    connected_to_modulo: bool
    openclaw_connected: bool
    hosting_enabled: bool
    worker_registered: bool
    worker_healthy: bool
    worker_id: str = ""
    worker_runtime_state: str = ""
    enabled_models_text: str = ""
    current_load: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    last_worker_error: str = ""
    smoke_test_ok: bool = False
    smoke_test_summary: str = "No smoke test run yet."
    smoke_test_details: str = ""


@dataclass
class GuiAppController:
    harness: LocalPrototypeHarness

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
            worker_id=worker.worker_id if worker else "",
            worker_runtime_state=worker.runtime_state.value if worker else WorkerRuntimeState.STOPPED.value,
            enabled_models_text=", ".join(worker.enabled_models) if worker and worker.enabled_models else "",
            current_load=worker.current_load if worker else 0,
            completed_jobs=worker.completed_jobs if worker else 0,
            failed_jobs=worker.failed_jobs if worker else 0,
            last_worker_error=onboarding.last_worker_error,
            smoke_test_ok=onboarding.smoke_test_ok,
            smoke_test_summary=self._smoke_test_summary(smoke_test),
            smoke_test_details=self._smoke_test_details(smoke_test),
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
