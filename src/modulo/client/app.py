from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from modulo.common.catalog import SUPPORTED_MODELS
from modulo.common.contracts import (
    WorkerBridgeConfig,
    WorkerStatusSnapshot,
    WorkerSupervisorCommand,
)
from modulo.worker.runtime import WorkerBridgeRuntime


@dataclass(frozen=True)
class SmokeTestResult:
    ok: bool
    model_id: str = ""
    user_message: str = ""
    response_text: str = ""
    error: str = ""


@dataclass(frozen=True)
class OpenClawConnectionStatus:
    connected: bool = False
    mode: str = "prototype-safe"
    summary: str = "OpenClaw is not connected yet."
    details: str = (
        "Modulo is not changing local OpenClaw configuration in this prototype flow."
    )
    safety_note: str = (
        "Safe prototype mode: the OpenClaw action only updates Modulo's in-app state."
    )


@dataclass(frozen=True)
class HostingSetupStatus:
    selected_model_id: str = ""
    available_model_ids: tuple[str, ...] = ()
    available_model_labels: tuple[str, ...] = ()
    readiness_summary: str = "Select a model to prepare hosting."
    readiness_details: str = ""
    can_enable_hosting: bool = False


@dataclass(frozen=True)
class ClientStatus:
    connected_to_modulo: bool = False
    openclaw_connected: bool = False
    hosting_enabled: bool = False
    openclaw: OpenClawConnectionStatus = OpenClawConnectionStatus()
    hosting_setup: HostingSetupStatus = HostingSetupStatus()
    worker: WorkerStatusSnapshot | None = None
    smoke_test: SmokeTestResult | None = None


@dataclass(frozen=True)
class OnboardingStatus:
    connected_to_modulo: bool
    openclaw_connected: bool
    hosting_enabled: bool
    worker_registered: bool
    worker_healthy: bool
    last_worker_error: str = ""
    smoke_test_ok: bool = False
    smoke_test_error: str = ""


class ClientSmokeTestRunner(Protocol):
    def run_smoke_test(self, user_message: str) -> SmokeTestResult:
        """Run a smoke test through the client-facing prototype path."""


@dataclass
class ModuloClientSupervisor:
    worker_bridge: WorkerBridgeRuntime
    connected_to_modulo: bool = True
    openclaw_connected: bool = False
    smoke_test_runner: ClientSmokeTestRunner | None = None
    _last_smoke_test: SmokeTestResult | None = None

    def configure_worker(self, config: WorkerBridgeConfig) -> ClientStatus:
        was_running = self.worker_bridge.get_status().desired_running
        if was_running:
            self.worker_bridge.stop()
        self.worker_bridge.config = config
        transport = self.worker_bridge.transport
        if hasattr(transport, "config"):
            object.__setattr__(transport, "config", config)
        self.worker_bridge.__post_init__()
        if was_running:
            self.worker_bridge.start()
        self._last_smoke_test = None
        return self.get_status()

    def set_hosting_model(self, model_id: str) -> ClientStatus:
        config = self.worker_bridge.config
        next_config = WorkerBridgeConfig(
            modulo_url=config.modulo_url,
            worker_id=config.worker_id,
            enabled_models=(model_id,),
            max_concurrency=config.max_concurrency,
            kind=config.kind,
        )
        return self.configure_worker(next_config)

    def connect_openclaw(self) -> ClientStatus:
        self.openclaw_connected = True
        return self.get_status()

    def disconnect_openclaw(self) -> ClientStatus:
        self.openclaw_connected = False
        return self.get_status()

    def apply_worker_command(self, command: WorkerSupervisorCommand) -> ClientStatus:
        if command is WorkerSupervisorCommand.START:
            self.worker_bridge.start()
        elif command is WorkerSupervisorCommand.STOP:
            self.worker_bridge.stop()
        elif command is WorkerSupervisorCommand.RESTART:
            self.worker_bridge.restart()
        return self.get_status()

    def start_hosting(self) -> ClientStatus:
        return self.apply_worker_command(WorkerSupervisorCommand.START)

    def stop_hosting(self) -> ClientStatus:
        return self.apply_worker_command(WorkerSupervisorCommand.STOP)

    def restart_hosting(self) -> ClientStatus:
        return self.apply_worker_command(WorkerSupervisorCommand.RESTART)

    def run_hosting_cycle(self) -> ClientStatus:
        self.worker_bridge.run_cycle()
        return self.get_status()

    def run_smoke_test(self, user_message: str = "Smoke test request") -> ClientStatus:
        if self.smoke_test_runner is None:
            self._last_smoke_test = SmokeTestResult(
                ok=False,
                user_message=user_message,
                error="No smoke test runner configured",
            )
            return self.get_status()

        self._last_smoke_test = self.smoke_test_runner.run_smoke_test(user_message)
        return self.get_status()

    def get_onboarding_status(self) -> OnboardingStatus:
        status = self.get_status()
        worker = status.worker
        smoke_test = status.smoke_test
        return OnboardingStatus(
            connected_to_modulo=status.connected_to_modulo,
            openclaw_connected=status.openclaw_connected,
            hosting_enabled=status.hosting_enabled,
            worker_registered=bool(worker and worker.registered_with_cloud),
            worker_healthy=bool(worker and worker.healthy),
            last_worker_error=worker.last_error if worker else "",
            smoke_test_ok=bool(smoke_test and smoke_test.ok),
            smoke_test_error=smoke_test.error if smoke_test else "",
        )

    def get_status(self) -> ClientStatus:
        worker_status = self.worker_bridge.get_status()
        return ClientStatus(
            connected_to_modulo=self.connected_to_modulo,
            openclaw_connected=self.openclaw_connected,
            hosting_enabled=worker_status.desired_running,
            openclaw=self.get_openclaw_status(),
            hosting_setup=self.get_hosting_setup_status(),
            worker=worker_status,
            smoke_test=self._last_smoke_test,
        )

    def get_openclaw_status(self) -> OpenClawConnectionStatus:
        if self.openclaw_connected:
            return OpenClawConnectionStatus(
                connected=True,
                summary="OpenClaw buyer path is marked connected in Modulo.",
                details=(
                    "This prototype uses a safe in-app connection state so the GUI can model "
                    "buyer onboarding without editing local OpenClaw files or settings."
                ),
            )
        return OpenClawConnectionStatus()

    def get_hosting_setup_status(self) -> HostingSetupStatus:
        selected_model_id = self.worker_bridge.config.enabled_models[0] if self.worker_bridge.config.enabled_models else ""
        available_models = tuple(SUPPORTED_MODELS.values())
        labels = tuple(f"{model.display_name} ({model.model_id})" for model in available_models)
        readiness_summary = self._hosting_readiness_summary(selected_model_id)
        return HostingSetupStatus(
            selected_model_id=selected_model_id,
            available_model_ids=tuple(model.model_id for model in available_models),
            available_model_labels=labels,
            readiness_summary=readiness_summary,
            readiness_details=self._hosting_readiness_details(selected_model_id),
            can_enable_hosting=bool(selected_model_id),
        )

    @staticmethod
    def _hosting_readiness_summary(selected_model_id: str) -> str:
        if not selected_model_id:
            return "Select a curated model to prepare hosting."
        return f"Ready to host with {selected_model_id}."

    @staticmethod
    def _hosting_readiness_details(selected_model_id: str) -> str:
        if not selected_model_id:
            return "No model is selected for hosting yet."
        model = SUPPORTED_MODELS.get(selected_model_id)
        if model is None:
            return "The selected model is outside the curated v1 catalog."
        return (
            f"Selected model: {model.display_name}\n"
            f"Runtime identity: {model.ollama_runtime_name}\n"
            "Hosting remains explicit and opt-in. Use Start Hosting when you are ready."
        )


def describe_default_actions() -> list[str]:
    """Return the primary v1 user actions for the tray-first client."""
    return [
        "Connect OpenClaw",
        "Enable hosting to earn",
    ]
