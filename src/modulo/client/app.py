from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Callable, Protocol

from modulo.common.catalog import SUPPORTED_MODELS
from modulo.client.openclaw_discovery import OpenClawDiscovery, OpenClawDiscoveryStatus
from modulo.client.ollama_discovery import OllamaDiscovery, OllamaDiscoveryStatus
from modulo.client.ollama_loaded_models import (
    LoadedOllamaModel,
    OllamaLoadedModelsDiscovery,
    OllamaLoadedModelsStatus,
)
from modulo.client.hosting_readiness import (
    HostingRuntimeProbeStatus,
    OllamaHostingRuntimeProbe,
)
from modulo.common.contracts import (
    WorkerBridgeConfig,
    WorkerStatusSnapshot,
    WorkerSupervisorCommand,
)
from modulo.worker.executors import StubExecutor
from modulo.worker.runtime import WorkerBridgeRuntime


@dataclass(frozen=True)
class SmokeTestResult:
    ok: bool
    model_id: str = ""
    user_message: str = ""
    response_text: str = ""
    error: str = ""
    execution_mode: str = ""
    execution_summary: str = ""


@dataclass(frozen=True)
class OpenClawConnectionPlan:
    available: bool = False
    staged: bool = False
    apply_ready: bool = False
    state: str = "not_staged"
    summary: str = "No OpenClaw connection plan has been staged yet."
    details: str = "Review the local OpenClaw state before planning any changes."
    change_lines: tuple[str, ...] = ()
    apply_label: str = "Apply staged plan"


@dataclass(frozen=True)
class OpenClawConfigurationStatus:
    configured: bool = False
    installed: bool = False
    config_present: bool = False
    state: str = "not_installed"
    mode: str = "prototype-safe"
    summary: str = "OpenClaw is not configured to route through Modulo yet."
    details: str = (
        "Modulo is not changing local OpenClaw configuration in this prototype flow."
    )
    safety_note: str = (
        "Safe prototype mode: the OpenClaw action only updates Modulo's setup state."
    )
    current_provider: str = ""
    current_primary_model: str = ""
    current_base_url: str = ""
    connection_plan: OpenClawConnectionPlan = OpenClawConnectionPlan()
    error: str = ""


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
class HostingPrewarmResult:
    ok: bool
    summary: str = ""
    detail: str = ""


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
    prototype_hosting_available: bool = False
    hosting_mode_label: str = "real"
    warm_state_badge: str = "UNKNOWN"
    warm_summary: str = "Warm-state visibility is unavailable."
    warm_details: tuple[str, ...] = ()
    loaded_model_ids: tuple[str, ...] = ()
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
class PlatformModelListing:
    model_id: str
    display_name: str
    source: str
    summary: str = ""


@dataclass(frozen=True)
class PlatformSessionStatus:
    connected: bool = False
    summary: str = "Platform session bridge is not configured yet."
    details: str = (
        "Attach a client-owned session bridge to fetch platform truth independently of hosting."
    )
    account_summary: str = "No account context has been fetched yet."
    network_models: tuple[PlatformModelListing, ...] = ()
    cloud_models: tuple[PlatformModelListing, ...] = ()
    credits_summary: str = "Unavailable"
    buyer_routing_summary: str = "Buyer routing state has not been fetched yet."
    buyer_config_summary: str = "Buyer model selection and routing preferences have not been fetched yet."


@dataclass(frozen=True)
class ClientStatus:
    connected_to_modulo: bool = False
    openclaw_configured: bool = False
    hosting_enabled: bool = False
    openclaw: OpenClawConfigurationStatus = OpenClawConfigurationStatus()
    platform: PlatformSessionStatus = PlatformSessionStatus()
    hosting_setup: HostingSetupStatus = HostingSetupStatus()
    activity: ActivityVisibilityStatus = ActivityVisibilityStatus()
    worker: WorkerStatusSnapshot | None = None
    smoke_test: SmokeTestResult | None = None


@dataclass(frozen=True)
class OnboardingStatus:
    connected_to_modulo: bool
    openclaw_configured: bool
    hosting_enabled: bool
    worker_registered: bool
    worker_healthy: bool
    last_worker_error: str = ""
    smoke_test_ok: bool = False
    smoke_test_error: str = ""


class ClientSmokeTestRunner(Protocol):
    def run_smoke_test(
        self,
        user_message: str,
        *,
        system_message: str = "",
    ) -> SmokeTestResult:
        """Run a smoke test through the client-facing prototype path."""


class ClientActivityProvider(Protocol):
    def get_activity_visibility(self) -> ActivityVisibilityStatus:
        """Return recent activity and continuity hints for the client."""


class ClientHostingRuntimeProbe(Protocol):
    def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
        """Probe the local runtime for selected hosting model readiness."""


class ClientSessionBridge(Protocol):
    def fetch_platform_status(self) -> PlatformSessionStatus:
        """Fetch client-owned platform state independently from the worker runtime."""


class ClientOpenClawDiscovery(Protocol):
    def discover(self) -> OpenClawDiscoveryStatus:
        """Detect local OpenClaw installation and config state."""


class ClientOllamaLoadedModelsDiscovery(Protocol):
    def discover(self) -> OllamaLoadedModelsStatus:
        """Detect which Ollama models are currently loaded in local memory."""


class ClientHostingPrewarmer(Protocol):
    def prewarm(self, model_id: str) -> HostingPrewarmResult:
        """Request that the selected Ollama model be loaded and kept warm locally."""


@dataclass
class ModuloClientSupervisor:
    worker_bridge: WorkerBridgeRuntime
    connected_to_modulo: bool = True
    openclaw_configured: bool = False
    session_bridge: ClientSessionBridge | None = None
    openclaw_discovery: ClientOpenClawDiscovery | None = None
    ollama_discovery: OllamaDiscovery | None = None
    ollama_loaded_models_discovery: ClientOllamaLoadedModelsDiscovery | None = None
    hosting_runtime_probe: ClientHostingRuntimeProbe = field(default_factory=OllamaHostingRuntimeProbe)
    hosting_prewarmer: ClientHostingPrewarmer | None = None
    smoke_test_runner: ClientSmokeTestRunner | None = None
    activity_provider: ClientActivityProvider | None = None
    hosting_model_changed_hook: Callable[[str], None] | None = None
    readiness_cache_ttl_seconds: float = 5.0
    _last_smoke_test: SmokeTestResult | None = None
    _cached_ollama_discovery: OllamaDiscoveryStatus | None = None
    _cached_ollama_discovery_at: float = 0.0
    _cached_ollama_loaded_models: OllamaLoadedModelsStatus | None = None
    _cached_ollama_loaded_models_at: float = 0.0
    _cached_openclaw_discovery: OpenClawDiscoveryStatus | None = None
    _cached_openclaw_discovery_at: float = 0.0
    _cached_runtime_probe: HostingRuntimeProbeStatus | None = None
    _cached_runtime_probe_model_id: str = ""
    _cached_runtime_probe_at: float = 0.0
    _staged_openclaw_plan: OpenClawConnectionPlan | None = None
    _prewarm_model_id: str = ""
    _prewarm_state: str = "idle"
    _prewarm_summary: str = ""
    _prewarm_detail: str = ""
    _last_prewarm_attempt_at: float = 0.0
    warm_maintenance_min_ttl_seconds: float = 120.0
    prewarm_retry_cooldown_seconds: float = 30.0

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
        self._reset_prewarm_state()
        config = self.worker_bridge.config
        next_config = WorkerBridgeConfig(
            modulo_url=config.modulo_url,
            worker_id=config.worker_id,
            enabled_models=(model_id,),
            max_concurrency=config.max_concurrency,
            kind=config.kind,
        )
        status = self.configure_worker(next_config)
        if self.hosting_model_changed_hook is not None:
            self.hosting_model_changed_hook(model_id)
            status = self.get_status()
        if status.hosting_enabled:
            return self._prewarm_selected_model()
        return status

    def stage_openclaw_connection(self) -> ClientStatus:
        self._staged_openclaw_plan = self._build_openclaw_connection_plan(
            self.get_openclaw_discovery_status()
        )
        return self.get_status()

    def apply_openclaw_connection_plan(self) -> ClientStatus:
        if self._staged_openclaw_plan is None:
            self._staged_openclaw_plan = self._build_openclaw_connection_plan(
                self.get_openclaw_discovery_status()
            )
        if self._staged_openclaw_plan.apply_ready:
            self.openclaw_configured = True
        return self.get_status()

    def configure_openclaw(self) -> ClientStatus:
        return self.stage_openclaw_connection()

    def apply_worker_command(self, command: WorkerSupervisorCommand) -> ClientStatus:
        if command is WorkerSupervisorCommand.START:
            self.worker_bridge.start()
        elif command is WorkerSupervisorCommand.STOP:
            self.worker_bridge.stop()
        elif command is WorkerSupervisorCommand.RESTART:
            self.worker_bridge.restart()
        return self.get_status()

    def start_hosting(self) -> ClientStatus:
        status = self.apply_worker_command(WorkerSupervisorCommand.START)
        if status.hosting_enabled:
            return self._prewarm_selected_model()
        return status

    def stop_hosting(self) -> ClientStatus:
        self._reset_prewarm_state()
        return self.apply_worker_command(WorkerSupervisorCommand.STOP)

    def restart_hosting(self) -> ClientStatus:
        self._reset_prewarm_state()
        status = self.apply_worker_command(WorkerSupervisorCommand.RESTART)
        if status.hosting_enabled:
            return self._prewarm_selected_model()
        return status

    def run_hosting_cycle(self) -> ClientStatus:
        self.worker_bridge.run_cycle()
        if self.worker_bridge.get_status().desired_running:
            return self._maintain_host_warmth()
        return self.get_status()

    def run_smoke_test(
        self,
        user_message: str = "Smoke test request",
        *,
        system_message: str = "",
    ) -> ClientStatus:
        if self.smoke_test_runner is None:
            self._last_smoke_test = SmokeTestResult(
                ok=False,
                user_message=user_message,
                error="No smoke test runner configured",
            )
            return self.get_status()

        self._last_smoke_test = self.smoke_test_runner.run_smoke_test(
            user_message,
            system_message=system_message,
        )
        return self.get_status()

    def get_onboarding_status(self) -> OnboardingStatus:
        status = self.get_status()
        worker = status.worker
        smoke_test = status.smoke_test
        return OnboardingStatus(
            connected_to_modulo=status.connected_to_modulo,
            openclaw_configured=status.openclaw_configured,
            hosting_enabled=status.hosting_enabled,
            worker_registered=bool(worker and worker.registered_with_cloud),
            worker_healthy=bool(worker and worker.healthy),
            last_worker_error=worker.last_error if worker else "",
            smoke_test_ok=bool(smoke_test and smoke_test.ok),
            smoke_test_error=smoke_test.error if smoke_test else "",
        )

    def get_status(self) -> ClientStatus:
        worker_status = self.worker_bridge.get_status()
        openclaw_status = self.get_openclaw_status()
        return ClientStatus(
            connected_to_modulo=self.connected_to_modulo,
            openclaw_configured=openclaw_status.configured,
            hosting_enabled=worker_status.desired_running,
            openclaw=openclaw_status,
            platform=self.get_platform_session_status(),
            hosting_setup=self.get_hosting_setup_status(),
            activity=self.get_activity_visibility(),
            worker=worker_status,
            smoke_test=self._last_smoke_test,
        )

    def get_openclaw_status(self) -> OpenClawConfigurationStatus:
        discovery = self.get_openclaw_discovery_status()
        connection_plan = self._staged_openclaw_plan or self._build_openclaw_connection_plan(discovery)
        if discovery.installed or discovery.config_present:
            details = discovery.details
            if self.openclaw_configured and not discovery.configured_for_modulo:
                details = (
                    f"{details}\n\nA prototype-safe configuration intent is staged in Modulo, "
                    "but the local OpenClaw config is not routing through Modulo yet. "
                    "This keeps the staged flow explicit without editing local OpenClaw files."
                )
            return OpenClawConfigurationStatus(
                configured=(discovery.configured_for_modulo or self.openclaw_configured),
                installed=discovery.installed,
                config_present=discovery.config_present,
                state=(
                    "staged_apply"
                    if self.openclaw_configured and not discovery.configured_for_modulo
                    else discovery.state
                ),
                mode=(
                    "staged_apply"
                    if self.openclaw_configured and not discovery.configured_for_modulo
                    else "discovery"
                ),
                summary=(
                    "Modulo has staged and applied a prototype-safe OpenClaw routing configuration, but the local OpenClaw files are not yet configured by this slice."
                    if self.openclaw_configured and not discovery.configured_for_modulo
                    else discovery.summary
                ),
                details=details,
                safety_note=(
                    "Staged apply mode: Modulo is still not changing local OpenClaw files in this "
                    "slice, but the explicit routing plan has been reviewed and applied inside "
                    "Modulo's use setup flow."
                    if self.openclaw_configured and not discovery.configured_for_modulo
                    else "Discovery mode: Modulo is reading local OpenClaw state but is not changing "
                    "local OpenClaw files in this slice."
                ),
                current_provider=discovery.current_provider,
                current_primary_model=discovery.current_primary_model,
                current_base_url=discovery.current_base_url,
                connection_plan=connection_plan,
                error=discovery.error,
            )
        if self.openclaw_configured:
            return OpenClawConfigurationStatus(
                configured=True,
                state="prototype_configured",
                summary="OpenClaw is configured in Modulo to route through the OpenClaw platform.",
                details=(
                    "This prototype uses a safe in-app setup state so the GUI can model "
                    "routing configuration without editing local OpenClaw files or settings."
                ),
                safety_note=(
                    "Safe prototype mode: this marks the use route as configured inside Modulo, "
                    "but it does not wrap or rewrite a local OpenClaw install."
                ),
                connection_plan=connection_plan,
            )
        return OpenClawConfigurationStatus(connection_plan=connection_plan)

    def get_openclaw_discovery_status(self) -> OpenClawDiscoveryStatus:
        now = time.monotonic()
        if (
            self._cached_openclaw_discovery is not None
            and now - self._cached_openclaw_discovery_at < self.readiness_cache_ttl_seconds
        ):
            return self._cached_openclaw_discovery
        discovery = self.openclaw_discovery or OpenClawDiscovery(
            modulo_url=self.worker_bridge.config.modulo_url,
        )
        status = discovery.discover()
        self._cached_openclaw_discovery = status
        self._cached_openclaw_discovery_at = now
        return status

    def get_hosting_setup_status(self) -> HostingSetupStatus:
        selected_model_id = self.worker_bridge.config.enabled_models[0] if self.worker_bridge.config.enabled_models else ""
        discovery = self.get_ollama_discovery_status()
        supported_models = tuple(SUPPORTED_MODELS.values())
        supported_model_ids = tuple(model.model_id for model in supported_models)
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
        available_model_ids = supported_installed_model_ids + unsupported_installed_model_ids
        available_model_labels = tuple(
            self._hosting_model_label(
                model_id,
                installed_model_ids=installed_model_ids,
            )
            for model_id in available_model_ids
        )
        prototype_hosting_available = self._prototype_hosting_available()
        preflight = self._hosting_preflight_status(
            selected_model_id=selected_model_id,
            discovery=discovery,
            installed_model_ids=installed_model_ids,
            runtime_probe=self.get_hosting_runtime_probe_status(selected_model_id),
        )
        loaded_models = self.get_ollama_loaded_models_status()
        warm_state_badge, warm_summary, warm_details = self._hosting_warm_state(
            selected_model_id=selected_model_id,
            loaded_status=loaded_models,
        )
        readiness_summary = self._hosting_readiness_summary(
            preflight=preflight,
            prototype_hosting_available=prototype_hosting_available,
        )
        return HostingSetupStatus(
            selected_model_id=selected_model_id,
            available_model_ids=available_model_ids,
            available_model_labels=available_model_labels,
            installed_model_ids=installed_model_ids,
            supported_installed_model_ids=supported_installed_model_ids,
            supported_missing_model_ids=supported_missing_model_ids,
            unsupported_installed_model_ids=unsupported_installed_model_ids,
            ollama_available=discovery.available,
            preflight=preflight,
            prototype_hosting_available=prototype_hosting_available,
            hosting_mode_label="prototype" if prototype_hosting_available else "real",
            warm_state_badge=warm_state_badge,
            warm_summary=warm_summary,
            warm_details=warm_details,
            loaded_model_ids=tuple(model.model_id for model in loaded_models.loaded_models),
            readiness_summary=readiness_summary,
            readiness_details=self._hosting_readiness_details(
                selected_model_id=selected_model_id,
                discovery=discovery,
                preflight=preflight,
                prototype_hosting_available=prototype_hosting_available,
                supported_installed_model_ids=supported_installed_model_ids,
                supported_missing_model_ids=supported_missing_model_ids,
                unsupported_installed_model_ids=unsupported_installed_model_ids,
            ),
            can_enable_hosting=(preflight.ok or prototype_hosting_available),
        )

    @staticmethod
    def _hosting_readiness_summary(
        *,
        preflight: HostingPreflightStatus,
        prototype_hosting_available: bool,
    ) -> str:
        if prototype_hosting_available and not preflight.ok:
            return (
                "Prototype hosting is available, but real local readiness is still blocked."
            )
        return preflight.summary

    @staticmethod
    def _hosting_readiness_details(
        *,
        selected_model_id: str,
        discovery: OllamaDiscoveryStatus,
        preflight: HostingPreflightStatus,
        prototype_hosting_available: bool,
        supported_installed_model_ids: tuple[str, ...],
        supported_missing_model_ids: tuple[str, ...],
        unsupported_installed_model_ids: tuple[str, ...],
    ) -> str:
        if not selected_model_id:
            return "No model is selected for hosting yet."
        model = SUPPORTED_MODELS.get(selected_model_id)
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
        selected_label = model.display_name if model is not None else selected_model_id
        selected_kind = (
            "Curated host model"
            if model is not None
            else "Installed local Ollama model"
        )
        mode_line = (
            "Hosting mode: prototype-safe demo path."
            if prototype_hosting_available
            else "Hosting mode: real local readiness required."
        )
        return (
            f"Selected model: {selected_label}\n"
            f"Model source: {selected_kind}\n"
            f"Runtime identity: {selected_model_id}\n"
            f"Supported and installed: {supported_installed_line}\n"
            f"Supported but missing: {supported_missing_line}\n"
            f"Installed but not curated: {unsupported_installed_line}\n"
            f"{mode_line}\n"
            f"Readiness result: {preflight.summary}\n"
            f"Blocking reason: {preflight.failure_reason or 'None'}\n"
            f"Ollama discovery: {discovery.summary}"
        )

    @staticmethod
    def _hosting_preflight_status(
        *,
        selected_model_id: str,
        discovery: OllamaDiscoveryStatus,
        installed_model_ids: tuple[str, ...],
        runtime_probe: HostingRuntimeProbeStatus,
    ) -> HostingPreflightStatus:
        checks: list[HostingPreflightCheck] = []
        curated = selected_model_id in SUPPORTED_MODELS

        has_model_selection = bool(selected_model_id)
        checks.append(
            HostingPreflightCheck(
                key="model_selected",
                ok=has_model_selection,
                summary="A hostable Ollama model is selected.",
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

        model_installed = selected_model_id in installed_model_ids if selected_model_id else False
        checks.append(
            HostingPreflightCheck(
                key="selected_model_installed",
                ok=model_installed,
                summary=(
                    "The selected curated model is installed locally."
                    if curated
                    else "The selected local Ollama model is installed locally."
                ),
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
                summary=HostingPreflightStatusSummary.for_check(
                    failed_check,
                    selected_model_id,
                    curated=curated,
                ),
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

    def get_ollama_loaded_models_status(self) -> OllamaLoadedModelsStatus:
        now = time.monotonic()
        if (
            self._cached_ollama_loaded_models is not None
            and now - self._cached_ollama_loaded_models_at < self.readiness_cache_ttl_seconds
        ):
            return self._cached_ollama_loaded_models
        discovery = self.ollama_loaded_models_discovery or OllamaLoadedModelsDiscovery()
        status = discovery.discover()
        self._cached_ollama_loaded_models = status
        self._cached_ollama_loaded_models_at = now
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

    def _prototype_hosting_available(self) -> bool:
        return isinstance(self.worker_bridge.executor, StubExecutor)

    @staticmethod
    def _hosting_model_label(
        model_id: str,
        *,
        installed_model_ids: tuple[str, ...],
    ) -> str:
        is_installed_locally = model_id in installed_model_ids
        canonical = SUPPORTED_MODELS.get(model_id)
        if canonical is not None:
            source_label = "local" if is_installed_locally else "network"
            source_icon = "🖥" if is_installed_locally else "☁"
            return (
                f"{source_icon} {canonical.display_name} "
                f"({canonical.model_id}, {source_label})"
            )
        return f"🖥 {model_id} (local)"

    def get_platform_session_status(self) -> PlatformSessionStatus:
        if self.session_bridge is None:
            return PlatformSessionStatus()
        return self.session_bridge.fetch_platform_status()

    def get_activity_visibility(self) -> ActivityVisibilityStatus:
        if self.activity_provider is None:
            return ActivityVisibilityStatus()
        return self.activity_provider.get_activity_visibility()

    def _invalidate_readiness_cache(self) -> None:
        self._cached_ollama_discovery = None
        self._cached_ollama_discovery_at = 0.0
        self._cached_ollama_loaded_models = None
        self._cached_ollama_loaded_models_at = 0.0
        self._cached_openclaw_discovery = None
        self._cached_openclaw_discovery_at = 0.0
        self._cached_runtime_probe = None
        self._cached_runtime_probe_model_id = ""
        self._cached_runtime_probe_at = 0.0

    def _hosting_warm_state(
        self,
        *,
        selected_model_id: str,
        loaded_status: OllamaLoadedModelsStatus,
    ) -> tuple[str, str, tuple[str, ...]]:
        if not selected_model_id:
            return (
                "NO MODEL",
                "Select a host model before checking warm state.",
                ("No host model is selected.",),
            )
        if not loaded_status.available:
            return (
                "UNKNOWN",
                loaded_status.summary,
                (loaded_status.details,),
            )

        loaded_model = next(
            (model for model in loaded_status.loaded_models if model.model_id == selected_model_id),
            None,
        )
        if loaded_model is None:
            if (
                selected_model_id == self._prewarm_model_id
                and self._prewarm_state == "failed"
            ):
                detail_lines = [self._prewarm_detail or "The latest prewarm attempt failed."]
                if loaded_status.loaded_models:
                    detail_lines.append(
                        f"Loaded models: {', '.join(model.model_id for model in loaded_status.loaded_models)}"
                    )
                return (
                    "WARM_FAILED",
                    self._prewarm_summary or f"Prewarm failed for {selected_model_id}.",
                    tuple(detail_lines),
                )
            if (
                selected_model_id == self._prewarm_model_id
                and self._prewarm_state == "warming"
            ):
                detail_lines = [self._prewarm_detail or "The selected model is being warmed locally."]
                if loaded_status.loaded_models:
                    detail_lines.append(
                        f"Loaded models: {', '.join(model.model_id for model in loaded_status.loaded_models)}"
                    )
                return (
                    "WARMING",
                    self._prewarm_summary or f"{selected_model_id} is warming locally.",
                    tuple(detail_lines),
                )
            return (
                "COLD",
                f"{selected_model_id} is not currently loaded in Ollama memory.",
                (
                    loaded_status.summary,
                    f"Loaded models: {', '.join(model.model_id for model in loaded_status.loaded_models) or 'None'}",
                ),
            )

        detail_lines = []
        if selected_model_id == self._prewarm_model_id and self._prewarm_detail:
            detail_lines.append(self._prewarm_detail)
        detail_lines.append(f"Loaded model: {loaded_model.model_id}")
        if loaded_model.expires_at:
            detail_lines.append(f"Expires at: {loaded_model.expires_at}")
        if loaded_model.size_vram_bytes:
            detail_lines.append(f"VRAM: {loaded_model.size_vram_bytes} bytes")
        if loaded_model.size_bytes:
            detail_lines.append(f"Loaded size: {loaded_model.size_bytes} bytes")
        if loaded_model.context_length:
            detail_lines.append(f"Context length: {loaded_model.context_length}")
        if loaded_model.family:
            detail_lines.append(f"Family: {loaded_model.family}")
        if loaded_model.parameter_size:
            detail_lines.append(f"Parameters: {loaded_model.parameter_size}")
        if loaded_model.quantization_level:
            detail_lines.append(f"Quantization: {loaded_model.quantization_level}")
        return (
            "WARM",
            (
                self._prewarm_summary
                if selected_model_id == self._prewarm_model_id and self._prewarm_summary
                else f"{selected_model_id} is currently loaded in Ollama memory."
            ),
            tuple(detail_lines),
        )

    def _prewarm_selected_model(self) -> ClientStatus:
        selected_model_id = (
            self.worker_bridge.config.enabled_models[0]
            if self.worker_bridge.config.enabled_models
            else ""
        )
        if not selected_model_id:
            return self.get_status()
        if self._prototype_hosting_available() or self.hosting_prewarmer is None:
            return self.get_status()

        self._prewarm_model_id = selected_model_id
        self._prewarm_state = "warming"
        self._prewarm_summary = f"Prewarming {selected_model_id} on the local Ollama runtime."
        self._prewarm_detail = "Modulo requested a lightweight host-side warmup for the selected model."
        self._last_prewarm_attempt_at = time.monotonic()

        try:
            result = self.hosting_prewarmer.prewarm(selected_model_id)
        except Exception as exc:
            result = HostingPrewarmResult(
                ok=False,
                summary=f"Prewarm failed for {selected_model_id}.",
                detail=str(exc),
            )

        self._cached_ollama_loaded_models = None
        self._cached_ollama_loaded_models_at = 0.0
        loaded_status = self.get_ollama_loaded_models_status()
        loaded_model_ids = {model.model_id for model in loaded_status.loaded_models}

        if result.ok and selected_model_id in loaded_model_ids:
            self._prewarm_state = "success"
            self._prewarm_summary = (
                result.summary or f"{selected_model_id} was prewarmed and is now loaded locally."
            )
            self._prewarm_detail = result.detail or "The selected model is currently loaded in local memory."
        elif result.ok:
            self._prewarm_state = "warming"
            self._prewarm_summary = result.summary or f"Prewarm is still settling for {selected_model_id}."
            self._prewarm_detail = result.detail or "The prewarm request succeeded, but the loaded-model view has not updated yet."
        else:
            self._prewarm_state = "failed"
            self._prewarm_summary = result.summary or f"Prewarm failed for {selected_model_id}."
            self._prewarm_detail = result.detail or "The selected model could not be warmed locally."

        return self.get_status()

    def _reset_prewarm_state(self) -> None:
        self._prewarm_model_id = ""
        self._prewarm_state = "idle"
        self._prewarm_summary = ""
        self._prewarm_detail = ""
        self._last_prewarm_attempt_at = 0.0

    def _maintain_host_warmth(self) -> ClientStatus:
        selected_model_id = (
            self.worker_bridge.config.enabled_models[0]
            if self.worker_bridge.config.enabled_models
            else ""
        )
        if not selected_model_id:
            return self.get_status()
        if self._prototype_hosting_available() or self.hosting_prewarmer is None:
            return self.get_status()

        self._cached_ollama_loaded_models = None
        self._cached_ollama_loaded_models_at = 0.0
        loaded_status = self.get_ollama_loaded_models_status()
        if self._should_refresh_warmth(selected_model_id, loaded_status):
            return self._prewarm_selected_model()
        return self.get_status()

    def _should_refresh_warmth(
        self,
        selected_model_id: str,
        loaded_status: OllamaLoadedModelsStatus,
    ) -> bool:
        if not self._prewarm_retry_allowed():
            return False
        if not loaded_status.available:
            return False

        loaded_model = next(
            (model for model in loaded_status.loaded_models if model.model_id == selected_model_id),
            None,
        )
        if loaded_model is None:
            return True

        expires_at = self._parse_ollama_timestamp(loaded_model.expires_at)
        if expires_at is None:
            return False
        remaining_seconds = (expires_at - datetime.now(timezone.utc)).total_seconds()
        return remaining_seconds <= self.warm_maintenance_min_ttl_seconds

    def _prewarm_retry_allowed(self) -> bool:
        now = time.monotonic()
        return now - self._last_prewarm_attempt_at >= self.prewarm_retry_cooldown_seconds

    @staticmethod
    def _parse_ollama_timestamp(value: str) -> datetime | None:
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _build_openclaw_connection_plan(
        self,
        discovery: OpenClawDiscoveryStatus,
    ) -> OpenClawConnectionPlan:
        if not discovery.installed:
            return OpenClawConnectionPlan(
                available=False,
                staged=self._staged_openclaw_plan is not None,
                apply_ready=False,
                state="not_installed",
                summary="OpenClaw is not installed, so there is no connection plan to apply yet.",
                details=(
                    "Install OpenClaw first. Once it is present locally, Modulo can stage a buyer "
                    "routing plan and explain the intended changes before applying anything."
                ),
                change_lines=(
                    "No local OpenClaw config changes would be made in the current state.",
                ),
                apply_label="Install OpenClaw first",
            )

        change_lines = [
            "Set the OpenClaw Ollama provider base URL to the Modulo endpoint.",
            "Keep routing scoped to the buyer-facing OpenClaw configuration flow.",
            "Run the buyer-path smoke test after the change is applied.",
        ]
        if discovery.current_primary_model:
            change_lines.append(
                f"Preserve visibility of the current primary model: {discovery.current_primary_model}."
            )

        if discovery.configured_for_modulo:
            return OpenClawConnectionPlan(
                available=True,
                staged=self._staged_openclaw_plan is not None,
                apply_ready=False,
                state="already_configured",
                summary="OpenClaw already appears to be routing through Modulo.",
                details=(
                    "Modulo can still review the detected buyer-routing state, but there is no new "
                    "routing change to apply right now."
                ),
                change_lines=tuple(change_lines),
                apply_label="Already routing through Modulo",
            )

        if discovery.config_present:
            details = (
                "Modulo would update the detected local OpenClaw config so buyer traffic targets the "
                "Modulo Ollama-compatible endpoint. This slice stages that plan explicitly but does "
                "not mutate local files yet."
            )
        else:
            details = (
                "Modulo would create or initialize the local OpenClaw routing config against the "
                "Modulo endpoint. This slice stages that plan explicitly but does not write files yet."
            )

        return OpenClawConnectionPlan(
            available=True,
            staged=self._staged_openclaw_plan is not None,
            apply_ready=True,
            state="ready_to_apply",
            summary="A buyer-routing connection plan is ready for review before apply.",
            details=details,
            change_lines=tuple(change_lines),
        )


class HostingPreflightStatusSummary:
    @staticmethod
    def for_check(check: HostingPreflightCheck, selected_model_id: str, *, curated: bool) -> str:
        if check.key == "model_selected":
            return "Select a local Ollama model to prepare hosting."
        if check.key == "ollama_available":
            return "Ollama is not available yet, so hosting is not ready."
        if check.key == "selected_model_installed":
            if curated:
                return f"{selected_model_id} is curated by Modulo but is not installed locally."
            return f"{selected_model_id} is not installed locally."
        if check.key == "runtime_model_probe":
            return f"The local Ollama runtime could not resolve {selected_model_id}."
        return "Hosting preflight did not pass."


def describe_default_actions() -> list[str]:
    """Return the primary v1 user actions for the tray-first client."""
    return [
        "Configure OpenClaw routing",
        "Enable hosting to earn",
    ]
