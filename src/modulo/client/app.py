from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Protocol

from modulo.common.catalog import SUPPORTED_MODELS
from modulo.client.ollama_discovery import OllamaDiscovery, OllamaDiscoveryStatus
from modulo.client.hosting_readiness import (
    HostingRuntimeProbeStatus,
    OllamaHostingRuntimeProbe,
)
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
class HostingPreflightCheck:
    key: str
    ok: bool
    summary: str
    detail: str = ""
    blocking: bool = True


@dataclass(frozen=True)
class HostingPreflightStatus:
    ok: bool = False
    summary: str = "Hosting preflight has not run."
    failure_reason: str = ""
    checks: tuple[HostingPreflightCheck, ...] = ()


@dataclass(frozen=True)
class HostingSetupStatus:
    selected_model_id: str = ""
    available_model_ids: tuple[str, ...] = ()
    available_model_labels: tuple[str, ...] = ()
    installed_model_ids: tuple[str, ...] = ()
    supported_installed_model_ids: tuple[str, ...] = ()
    supported_missing_model_ids: tuple[str, ...] = ()
    unsupported_installed_model_ids: tuple[str, ...] = ()
    ollama_available: bool = False
    preflight: HostingPreflightStatus = HostingPreflightStatus()
    readiness_summary: str = "Select a model to prepare hosting."
    readiness_details: str = ""
    can_enable_hosting: bool = False


@dataclass(frozen=True)
class ActivityEntry:
    job_id: str
    buyer_id: str = ""
    model_id: str = ""
    worker_id: str = ""
    status: str = ""
    continuity_hint: str = ""
    summary: str = ""


@dataclass(frozen=True)
class ActivityVisibilityStatus:
    continuity_summary: str = "No buyer continuity activity yet."
    recent_activity: tuple[ActivityEntry, ...] = ()


@dataclass(frozen=True)
class ClientStatus:
    connected_to_modulo: bool = False
    openclaw_connected: bool = False
    hosting_enabled: bool = False
    openclaw: OpenClawConnectionStatus = OpenClawConnectionStatus()
    hosting_setup: HostingSetupStatus = HostingSetupStatus()
    activity: ActivityVisibilityStatus = ActivityVisibilityStatus()
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


class ClientActivityProvider(Protocol):
    def get_activity_visibility(self) -> ActivityVisibilityStatus:
        """Return recent activity and continuity hints for the client."""


class ClientHostingRuntimeProbe(Protocol):
    def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
        """Probe the local runtime for selected hosting model readiness."""


@dataclass
class ModuloClientSupervisor:
    worker_bridge: WorkerBridgeRuntime
    connected_to_modulo: bool = True
    openclaw_connected: bool = False
    ollama_discovery: OllamaDiscovery | None = None
    hosting_runtime_probe: ClientHostingRuntimeProbe = field(default_factory=OllamaHostingRuntimeProbe)
    smoke_test_runner: ClientSmokeTestRunner | None = None
    activity_provider: ClientActivityProvider | None = None
    readiness_cache_ttl_seconds: float = 5.0
    _last_smoke_test: SmokeTestResult | None = None
    _cached_ollama_discovery: OllamaDiscoveryStatus | None = None
    _cached_ollama_discovery_at: float = 0.0
    _cached_runtime_probe: HostingRuntimeProbeStatus | None = None
    _cached_runtime_probe_model_id: str = ""
    _cached_runtime_probe_at: float = 0.0

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
        self._invalidate_readiness_cache()
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
            activity=self.get_activity_visibility(),
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
        discovery = self.get_ollama_discovery_status()
        available_models = tuple(SUPPORTED_MODELS.values())
        labels = tuple(f"{model.display_name} ({model.model_id})" for model in available_models)
        supported_model_ids = tuple(model.model_id for model in available_models)
        installed_model_ids = discovery.installed_model_ids
        supported_installed_model_ids = tuple(
            model_id for model_id in supported_model_ids if model_id in installed_model_ids
        )
        supported_missing_model_ids = tuple(
            model_id for model_id in supported_model_ids if model_id not in installed_model_ids
        )
        unsupported_installed_model_ids = tuple(
            model_id for model_id in installed_model_ids if model_id not in supported_model_ids
        )
        preflight = self._hosting_preflight_status(
            selected_model_id=selected_model_id,
            discovery=discovery,
            supported_installed_model_ids=supported_installed_model_ids,
            runtime_probe=self.get_hosting_runtime_probe_status(selected_model_id),
        )
        readiness_summary = self._hosting_readiness_summary(
            preflight=preflight,
        )
        return HostingSetupStatus(
            selected_model_id=selected_model_id,
            available_model_ids=supported_model_ids,
            available_model_labels=labels,
            installed_model_ids=installed_model_ids,
            supported_installed_model_ids=supported_installed_model_ids,
            supported_missing_model_ids=supported_missing_model_ids,
            unsupported_installed_model_ids=unsupported_installed_model_ids,
            ollama_available=discovery.available,
            preflight=preflight,
            readiness_summary=readiness_summary,
            readiness_details=self._hosting_readiness_details(
                selected_model_id=selected_model_id,
                discovery=discovery,
                preflight=preflight,
                supported_installed_model_ids=supported_installed_model_ids,
                supported_missing_model_ids=supported_missing_model_ids,
                unsupported_installed_model_ids=unsupported_installed_model_ids,
            ),
            can_enable_hosting=preflight.ok,
        )

    @staticmethod
    def _hosting_readiness_summary(
        *,
        preflight: HostingPreflightStatus,
    ) -> str:
        return preflight.summary

    @staticmethod
    def _hosting_readiness_details(
        *,
        selected_model_id: str,
        discovery: OllamaDiscoveryStatus,
        preflight: HostingPreflightStatus,
        supported_installed_model_ids: tuple[str, ...],
        supported_missing_model_ids: tuple[str, ...],
        unsupported_installed_model_ids: tuple[str, ...],
    ) -> str:
        if not selected_model_id:
            return "No model is selected for hosting yet."
        model = SUPPORTED_MODELS.get(selected_model_id)
        if model is None:
            return "The selected model is outside the curated v1 catalog."
        supported_installed_line = (
            ", ".join(supported_installed_model_ids)
            if supported_installed_model_ids
            else "None"
        )
        supported_missing_line = (
            ", ".join(supported_missing_model_ids)
            if supported_missing_model_ids
            else "None"
        )
        unsupported_installed_line = (
            ", ".join(unsupported_installed_model_ids)
            if unsupported_installed_model_ids
            else "None"
        )
        check_lines = "\n".join(
            f"- {'PASS' if check.ok else 'FAIL'} {check.summary}"
            for check in preflight.checks
        )
        return (
            f"Selected model: {model.display_name}\n"
            f"Runtime identity: {model.ollama_runtime_name}\n"
            f"Preflight: {preflight.summary}\n"
            f"Blocking reason: {preflight.failure_reason or 'None'}\n"
            f"Ollama discovery: {discovery.summary}\n"
            f"Supported and installed: {supported_installed_line}\n"
            f"Supported but missing: {supported_missing_line}\n"
            f"Installed but not curated: {unsupported_installed_line}\n"
            f"Checks:\n{check_lines}\n"
            "Hosting remains explicit and opt-in. Use Start Hosting when you are ready."
        )

    @staticmethod
    def _hosting_preflight_status(
        *,
        selected_model_id: str,
        discovery: OllamaDiscoveryStatus,
        supported_installed_model_ids: tuple[str, ...],
        runtime_probe: HostingRuntimeProbeStatus,
    ) -> HostingPreflightStatus:
        checks: list[HostingPreflightCheck] = []

        has_model_selection = bool(selected_model_id)
        checks.append(
            HostingPreflightCheck(
                key="model_selected",
                ok=has_model_selection,
                summary="A curated hosting model is selected.",
                detail=selected_model_id or "No curated model selected.",
            )
        )

        checks.append(
            HostingPreflightCheck(
                key="ollama_available",
                ok=discovery.available,
                summary="Ollama is available locally.",
                detail=discovery.summary,
            )
        )

        model_installed = selected_model_id in supported_installed_model_ids if selected_model_id else False
        checks.append(
            HostingPreflightCheck(
                key="selected_model_installed",
                ok=model_installed,
                summary="The selected curated model is installed locally.",
                detail=selected_model_id or "No selected model.",
            )
        )

        runtime_reachable = runtime_probe.reachable if selected_model_id else False
        checks.append(
            HostingPreflightCheck(
                key="runtime_model_probe",
                ok=runtime_reachable,
                summary="The local Ollama runtime can resolve the selected model.",
                detail=runtime_probe.detail or runtime_probe.summary,
            )
        )

        failed_check = next((check for check in checks if not check.ok and check.blocking), None)
        if failed_check is not None:
            return HostingPreflightStatus(
                ok=False,
                summary=HostingPreflightStatusSummary.for_check(failed_check, selected_model_id),
                failure_reason=failed_check.detail or failed_check.summary,
                checks=tuple(checks),
            )

        return HostingPreflightStatus(
            ok=True,
            summary=f"Hosting preflight passed for {selected_model_id}.",
            checks=tuple(checks),
        )

    def get_ollama_discovery_status(self) -> OllamaDiscoveryStatus:
        now = time.monotonic()
        if (
            self._cached_ollama_discovery is not None
            and now - self._cached_ollama_discovery_at < self.readiness_cache_ttl_seconds
        ):
            return self._cached_ollama_discovery
        if self.ollama_discovery is None:
            status = OllamaDiscoveryStatus(
                summary="Ollama discovery is not configured.",
                details="Attach a discovery provider before using live local model detection.",
                error="no discovery provider configured",
            )
        else:
            status = self.ollama_discovery.discover()
        self._cached_ollama_discovery = status
        self._cached_ollama_discovery_at = now
        return status

    def get_hosting_runtime_probe_status(self, model_id: str) -> HostingRuntimeProbeStatus:
        if not model_id:
            return HostingRuntimeProbeStatus(
                reachable=False,
                model_ready=False,
                summary="No hosting model selected for runtime probe.",
                detail="Select a curated model before probing the runtime.",
            )
        now = time.monotonic()
        if (
            self._cached_runtime_probe is not None
            and self._cached_runtime_probe_model_id == model_id
            and now - self._cached_runtime_probe_at < self.readiness_cache_ttl_seconds
        ):
            return self._cached_runtime_probe
        status = self.hosting_runtime_probe.probe(model_id)
        self._cached_runtime_probe = status
        self._cached_runtime_probe_model_id = model_id
        self._cached_runtime_probe_at = now
        return status

    def get_activity_visibility(self) -> ActivityVisibilityStatus:
        if self.activity_provider is None:
            return ActivityVisibilityStatus()
        return self.activity_provider.get_activity_visibility()

    def _invalidate_readiness_cache(self) -> None:
        self._cached_ollama_discovery = None
        self._cached_ollama_discovery_at = 0.0
        self._cached_runtime_probe = None
        self._cached_runtime_probe_model_id = ""
        self._cached_runtime_probe_at = 0.0


class HostingPreflightStatusSummary:
    @staticmethod
    def for_check(check: HostingPreflightCheck, selected_model_id: str) -> str:
        if check.key == "model_selected":
            return "Select a curated model to prepare hosting."
        if check.key == "ollama_available":
            return "Ollama is not available yet, so hosting is not ready."
        if check.key == "selected_model_installed":
            return f"{selected_model_id} is curated by Modulo but is not installed locally."
        if check.key == "runtime_model_probe":
            return f"The local Ollama runtime could not resolve {selected_model_id}."
        return "Hosting preflight did not pass."


def describe_default_actions() -> list[str]:
    """Return the primary v1 user actions for the tray-first client."""
    return [
        "Connect OpenClaw",
        "Enable hosting to earn",
    ]
