from __future__ import annotations

from dataclasses import dataclass

from modulo.common.contracts import (
    WorkerBridgeConfig,
    WorkerStatusSnapshot,
    WorkerSupervisorCommand,
)
from modulo.worker.runtime import WorkerBridgeRuntime


@dataclass(frozen=True)
class ClientStatus:
    connected_to_modulo: bool = False
    openclaw_connected: bool = False
    hosting_enabled: bool = False
    worker: WorkerStatusSnapshot | None = None


@dataclass
class ModuloClientSupervisor:
    worker_bridge: WorkerBridgeRuntime
    connected_to_modulo: bool = True
    openclaw_connected: bool = False

    def configure_worker(self, config: WorkerBridgeConfig) -> ClientStatus:
        self.worker_bridge.config = config
        self.worker_bridge.__post_init__()
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

    def get_status(self) -> ClientStatus:
        worker_status = self.worker_bridge.get_status()
        return ClientStatus(
            connected_to_modulo=self.connected_to_modulo,
            openclaw_connected=self.openclaw_connected,
            hosting_enabled=worker_status.desired_running,
            worker=worker_status,
        )


def describe_default_actions() -> list[str]:
    """Return the primary v1 user actions for the tray-first client."""
    return [
        "Connect OpenClaw",
        "Enable hosting to earn",
    ]

