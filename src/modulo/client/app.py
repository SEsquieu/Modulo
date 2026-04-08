from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
class ClientStatus:
    connected_to_modulo: bool = False
    openclaw_connected: bool = False
    hosting_enabled: bool = False
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
        self.worker_bridge.config = config
        self.worker_bridge.__post_init__()
        self._last_smoke_test = None
        return self.get_status()

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
            worker=worker_status,
            smoke_test=self._last_smoke_test,
        )


def describe_default_actions() -> list[str]:
    """Return the primary v1 user actions for the tray-first client."""
    return [
        "Connect OpenClaw",
        "Enable hosting to earn",
    ]
