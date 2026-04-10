from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass, field
from http.server import ThreadingHTTPServer
from urllib import request
from urllib import error as urllib_error

from modulo.client.app import (
    ActivityEntry,
    ActivityVisibilityStatus,
    ClientSessionBridge,
    ClientStatus,
    HostingPrewarmResult,
    ModuloClientSupervisor,
    PlatformModelListing,
    PlatformSessionStatus,
    SmokeTestResult,
)
from modulo.client.openclaw_discovery import OpenClawDiscovery
from modulo.client.ollama_discovery import OllamaDiscovery
from modulo.client.ollama_loaded_models import OllamaLoadedModelsDiscovery
from modulo.client.hosting_readiness import HostingRuntimeProbeStatus, OllamaHostingRuntimeProbe
from modulo.cloud.http import ModuloHTTPApp, build_http_server
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService
from modulo.common.catalog import SUPPORTED_MODELS
from modulo.common.contracts import JobStatus, RouteScope, WorkerBridgeConfig, WorkerRuntimeState
from modulo.worker.executors import OllamaExecutor, OllamaHTTPClient, StubExecutor, UrllibOllamaHTTPClient
from modulo.worker.errors import WorkerExecutionError
from modulo.worker.runtime import InMemoryWorkerRuntime, WorkerBridgeRuntime, WorkerExecutor
from modulo.worker.transport import UrllibWorkerHTTPTransport

GUI_SMOKE_TEST_USER_PROMPT = "Return the Modulo smoke test acknowledgment."
GUI_SMOKE_TEST_SYSTEM_PROMPT = (
    "You are responding to a Modulo GUI smoke test. "
    "Do not ask follow-up questions. "
    "Reply with exactly: MODULO_SMOKE_TEST_OK"
)
PROTOTYPE_PRIVATE_NETWORK_ID = "prototype-private"


@dataclass(frozen=True)
class PrototypeRoundTripResult:
    job_id: str
    trace_id: str
    model_id: str
    buyer_id: str
    assigned_worker_id: str
    user_message: str
    response_text: str
    execution_mode: str
    execution_summary: str
    client_status: ClientStatus


@dataclass(frozen=True)
class LocalPrototypeSessionBridge(ClientSessionBridge):
    service: InMemoryModuloService

    def fetch_platform_status(self) -> PlatformSessionStatus:
        workers = self.service.registry.list_workers()
        healthy_network_workers = [
            worker for worker in workers if worker.healthy and worker.kind.value == "network"
        ]

        network_models: dict[str, PlatformModelListing] = {}
        for worker in healthy_network_workers:
            for advertised_model in worker.advertised_models:
                canonical = SUPPORTED_MODELS.get(advertised_model.model_id)
                display_name = (
                    canonical.display_name if canonical is not None else advertised_model.model_id
                )
                network_models.setdefault(
                    advertised_model.model_id,
                    PlatformModelListing(
                        model_id=advertised_model.model_id,
                        display_name=display_name,
                        source="network",
                        summary=f"Advertised by healthy network worker {worker.worker_id}.",
                    ),
                )

        cloud_models = tuple(
            PlatformModelListing(
                model_id=model.model_id,
                display_name=model.display_name,
                source="cloud",
                summary="Prototype-safe placeholder trusted cloud catalog.",
            )
            for model in SUPPORTED_MODELS.values()
        )

        if network_models:
            network_summary = (
                f"{len(network_models)} network model(s) are currently advertised by healthy workers."
            )
        else:
            network_summary = "No network models are currently advertised in the local prototype."

        health = self.service.health_summary()
        details = (
            f"Healthy workers: {health['healthy_workers']} / {health['total_workers']}. "
            "Cloud catalog is still a prototype-safe placeholder."
        )
        return PlatformSessionStatus(
            connected=True,
            summary="Platform session bridge is connected to the local prototype control plane.",
            details=details,
            account_summary="Prototype account context is local-only and not authenticated yet.",
            network_models=tuple(network_models.values()),
            cloud_models=cloud_models,
            credits_summary="Prototype credits are not implemented yet.",
            buyer_routing_summary=network_summary,
            buyer_config_summary=(
                "Buyer routing defaults to platform-managed selection in the local prototype."
            ),
        )


@dataclass(frozen=True)
class LocalOllamaModelPrewarmer:
    base_url: str = "http://127.0.0.1:11434"
    keep_alive: str = "10m"
    timeout_seconds: float = 60.0

    def prewarm(self, model_id: str) -> HostingPrewarmResult:
        endpoint = f"{self.base_url.rstrip('/')}/api/generate"
        payload = json.dumps(
            {
                "model": model_id,
                "stream": False,
                "keep_alive": self.keep_alive,
            }
        ).encode("utf-8")
        req = request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                response.read()
        except Exception as exc:
            raise WorkerExecutionError(f"Ollama prewarm failed: {exc}") from exc

        return HostingPrewarmResult(
            ok=True,
            summary=f"Prewarm requested for {model_id}.",
            detail=f"Modulo asked Ollama to keep {model_id} warm for {self.keep_alive}.",
        )


@dataclass
class LocalPrototypeHarness:
    model_id: str = "llama3.1:8b"
    worker_id: str = "local-prototype-worker"
    buyer_id: str = "prototype-buyer"
    modulo_url: str = "http://127.0.0.1:8000"
    stub_response_text: str = "Hello from the Modulo local prototype worker."
    executor: WorkerExecutor | None = None
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_http_client: OllamaHTTPClient | None = None
    ollama_timeout_seconds: float = 120.0
    openclaw_discovery: OpenClawDiscovery | None = None
    ollama_discovery: OllamaDiscovery | None = None
    ollama_loaded_models_discovery: OllamaLoadedModelsDiscovery | None = None
    hosting_runtime_probe: OllamaHostingRuntimeProbe | None = None
    hosting_prewarmer: LocalOllamaModelPrewarmer | None = None
    selected_executor_mode: str = field(init=False, default="prototype")
    selected_executor_summary: str = field(init=False, default="")
    _explicit_executor_override: bool = field(init=False, default=False)
    service: InMemoryModuloService = field(init=False)
    cloud_runtime: InMemoryWorkerRuntime = field(init=False)
    app: ModuloHTTPApp = field(init=False)
    client: ModuloClientSupervisor = field(init=False)
    server: ThreadingHTTPServer | None = field(init=False, default=None)
    server_thread: threading.Thread | None = field(init=False, default=None)
    worker_loop_thread: threading.Thread | None = field(init=False, default=None)
    _worker_loop_stop: threading.Event = field(init=False, default_factory=threading.Event)
    _worker_loop_interval_seconds: float = field(init=False, default=0.02)
    platform_bind_port: int = field(init=False, default=0)
    lan_platform_url: str = field(init=False, default="")

    def __post_init__(self) -> None:
        self.service = InMemoryModuloService(router=TrustRouter())
        self.cloud_runtime = InMemoryWorkerRuntime()
        self.app = ModuloHTTPApp(
            service=self.service,
            runtime=self.cloud_runtime,
            inline_chat_execution=False,
            chat_wait_timeout_seconds=5.0,
            chat_wait_poll_seconds=0.02,
        )

        executor = self._select_executor()
        if hasattr(executor, "register_worker"):
            executor.register_worker(self.worker_id, self.stub_response_text)

        server = build_http_server(
            "0.0.0.0",
            0,
            service=self.service,
            runtime=self.cloud_runtime,
            app=self.app,
        )
        self.server = server
        _, port = server.server_address
        self.platform_bind_port = port
        self.modulo_url = f"http://127.0.0.1:{port}"
        lan_ip = self._discover_lan_ip()
        if lan_ip:
            self.lan_platform_url = f"http://{lan_ip}:{port}"
        self.server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        self.server_thread.start()

        config = WorkerBridgeConfig(
            modulo_url=self.modulo_url,
            worker_id=self.worker_id,
            enabled_models=(self.model_id,),
            serving_scope=RouteScope.PRIVATE,
            private_network_id=PROTOTYPE_PRIVATE_NETWORK_ID,
        )
        bridge = WorkerBridgeRuntime(
            config=config,
            transport=UrllibWorkerHTTPTransport(config=config),
            executor=executor,
        )
        self.client = ModuloClientSupervisor(
            worker_bridge=bridge,
            session_bridge=LocalPrototypeSessionBridge(service=self.service),
            openclaw_discovery=self.openclaw_discovery or OpenClawDiscovery(modulo_url=self.modulo_url),
            ollama_discovery=self.ollama_discovery or OllamaDiscovery(),
            ollama_loaded_models_discovery=self.ollama_loaded_models_discovery or OllamaLoadedModelsDiscovery(),
            hosting_runtime_probe=self.hosting_runtime_probe or OllamaHostingRuntimeProbe(),
            hosting_prewarmer=self.hosting_prewarmer or LocalOllamaModelPrewarmer(base_url=self.ollama_base_url),
            smoke_test_runner=self,
            activity_provider=self,
            hosting_model_changed_hook=self._on_hosting_model_changed,
        )
        self._sync_initial_hosting_model()

    def _select_executor(self) -> WorkerExecutor:
        if self.executor is not None:
            self._explicit_executor_override = True
            self.selected_executor_mode = "explicit"
            self.selected_executor_summary = "Prototype harness is using an explicitly supplied executor."
            return self.executor

        return self._executor_for_model(self.model_id)

    def _executor_for_model(self, model_id: str) -> WorkerExecutor:
        runtime_probe = self.hosting_runtime_probe or OllamaHostingRuntimeProbe()
        probe_status = runtime_probe.probe(model_id)
        self.hosting_runtime_probe = runtime_probe
        if probe_status.reachable and probe_status.model_ready:
            self.selected_executor_mode = "real"
            self.selected_executor_summary = probe_status.summary
            return OllamaExecutor(
                base_url=self.ollama_base_url,
                http_client=self.ollama_http_client or UrllibOllamaHTTPClient(timeout_seconds=self.ollama_timeout_seconds),
            )

        self.selected_executor_mode = "prototype"
        self.selected_executor_summary = probe_status.summary
        stub_executor = StubExecutor()
        stub_executor.register_worker(self.worker_id, self.stub_response_text)
        return stub_executor

    def _current_model_id(self) -> str:
        enabled_models = self.client.worker_bridge.config.enabled_models
        if enabled_models:
            return enabled_models[0]
        return self.model_id

    def _on_hosting_model_changed(self, model_id: str) -> None:
        self.model_id = model_id
        if self._explicit_executor_override:
            return
        self.client.worker_bridge.executor = self._executor_for_model(model_id)

    def _sync_initial_hosting_model(self) -> None:
        status = self.client.get_status()
        available_model_ids = status.hosting_setup.available_model_ids
        if not available_model_ids:
            return
        current_model_id = status.hosting_setup.selected_model_id
        if current_model_id in available_model_ids:
            return
        self.client.set_hosting_model(available_model_ids[0])

    def boot(self) -> ClientStatus:
        status = self.client.start_hosting()
        self._ensure_worker_loop_running()
        return status

    def shutdown(self) -> ClientStatus:
        self._stop_worker_loop()
        status = self.client.stop_hosting()
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.server_thread is not None:
            self.server_thread.join(timeout=2.0)
            self.server_thread = None
        return status

    def run_round_trip(
        self,
        user_message: str,
        *,
        buyer_id: str | None = None,
        system_message: str = "",
    ) -> PrototypeRoundTripResult:
        if not self.client.get_status().hosting_enabled:
            self.boot()
        else:
            self._ensure_worker_loop_running()

        effective_buyer_id = buyer_id or self.buyer_id
        current_model_id = self._current_model_id()
        body = {
            "model": current_model_id,
            "buyer_id": effective_buyer_id,
            "scope": "private",
            "private_network_id": PROTOTYPE_PRIVATE_NETWORK_ID,
            "messages": [],
            "stream": False,
        }
        if system_message:
            body["messages"].append({"role": "system", "content": system_message})
        body["messages"].append({"role": "user", "content": user_message})

        req = request.Request(
            f"{self.modulo_url.rstrip('/')}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            error_payload = json.loads(exc.read().decode("utf-8")) if exc.fp is not None else {}
            message = error_payload.get("error", str(exc)) if isinstance(error_payload, dict) else str(exc)
            raise RuntimeError(
                f"Prototype HTTP round trip did not complete successfully: {message}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Prototype ingress request failed: {exc}") from exc

        status = self.client.get_status()
        completed_job = self.service.jobs.list_jobs()[-1] if self.service.jobs.list_jobs() else None
        if completed_job is None or not completed_job.response_text:
            worker_error = status.worker.last_error if status.worker is not None else ""
            detail = f": {worker_error}" if worker_error else ""
            raise RuntimeError(f"Prototype HTTP round trip did not complete successfully{detail}")
        traces = self.service.list_traces()
        trace_id = traces[-1].trace_id if traces else ""

        return PrototypeRoundTripResult(
            job_id=completed_job.job_id,
            trace_id=trace_id,
            model_id=completed_job.request.model_id,
            buyer_id=effective_buyer_id,
            assigned_worker_id=completed_job.assigned_worker_id,
            user_message=user_message,
            response_text=payload.get("message", {}).get("content", completed_job.response_text),
            execution_mode=self.selected_executor_mode,
            execution_summary=self.selected_executor_summary,
            client_status=status,
        )

    def run_smoke_test(
        self,
        user_message: str,
        *,
        system_message: str = "",
    ) -> SmokeTestResult:
        try:
            result = self.run_round_trip(user_message, system_message=system_message)
        except RuntimeError as exc:
            return SmokeTestResult(
                ok=False,
                user_message=user_message,
                error=str(exc),
                execution_mode=self.selected_executor_mode,
                execution_summary=self.selected_executor_summary,
            )
        return SmokeTestResult(
            ok=True,
            model_id=result.model_id,
            user_message=result.user_message,
            response_text=result.response_text,
            execution_mode=result.execution_mode,
            execution_summary=result.execution_summary,
        )

    def get_activity_visibility(self) -> ActivityVisibilityStatus:
        jobs = sorted(
            self.service.jobs.list_jobs(),
            key=lambda job: job.job_id,
            reverse=True,
        )
        recent_entries = tuple(self._activity_entry_for_job(job) for job in jobs[:5])
        continuity_summary = self._continuity_summary(jobs)
        return ActivityVisibilityStatus(
            continuity_summary=continuity_summary,
            recent_activity=recent_entries,
        )

    def _activity_entry_for_job(self, job) -> ActivityEntry:
        continuity_hint = self._continuity_hint(job)
        buyer_label = job.request.buyer_id or "anonymous buyer"
        summary = (
            f"{buyer_label} requested {job.request.model_id} and landed on "
            f"{job.assigned_worker_id}."
        )
        if job.status is JobStatus.FAILED and job.failure_reason:
            summary = f"{summary} Final state: {job.failure_reason}"
        return ActivityEntry(
            job_id=job.job_id,
            buyer_id=job.request.buyer_id,
            model_id=job.request.model_id,
            worker_id=job.assigned_worker_id,
            status=job.status.value,
            continuity_hint=continuity_hint,
            summary=summary,
        )

    def _continuity_summary(self, jobs) -> str:
        if not jobs:
            return "No buyer continuity activity yet."
        leased_jobs = [job for job in jobs if "leased worker" in job.route.reason.lower()]
        if leased_jobs:
            latest = leased_jobs[0]
            buyer_label = latest.request.buyer_id or "recent buyer"
            return (
                f"Buyer continuity reused {latest.assigned_worker_id} for {buyer_label} "
                f"on {latest.request.model_id}."
            )
        latest = jobs[0]
        return (
            f"Latest routing sent {latest.request.model_id} to {latest.assigned_worker_id}. "
            "Run another request from the same buyer to exercise continuity."
        )

    @staticmethod
    def _continuity_hint(job) -> str:
        if "leased worker" in job.route.reason.lower():
            return "Continuity lease reused"
        if job.attempts > 1:
            return "Retried onto a different worker"
        return "Fresh routing decision"

    def _ensure_worker_loop_running(self) -> None:
        if self.worker_loop_thread is not None and self.worker_loop_thread.is_alive():
            return
        self._worker_loop_stop.clear()
        self.worker_loop_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_loop_thread.start()

    def _stop_worker_loop(self) -> None:
        self._worker_loop_stop.set()
        if self.worker_loop_thread is not None:
            self.worker_loop_thread.join(timeout=2.0)
            self.worker_loop_thread = None

    def _worker_loop(self) -> None:
        while not self._worker_loop_stop.is_set():
            status = self.client.get_status()
            if status.hosting_enabled and (
                status.worker is None or status.worker.runtime_state is not WorkerRuntimeState.ERROR
            ):
                self.client.run_hosting_cycle()
            time.sleep(self._worker_loop_interval_seconds)

    def run_debug_platform_probe(
        self,
        *,
        platform_url: str,
        private_network_id: str,
        model_id: str,
        user_message: str = "Say hello from the Modulo debug tab.",
        buyer_id: str = "buyer-debug",
    ) -> SmokeTestResult:
        target_url = platform_url.strip() or self.modulo_url
        network_id = private_network_id.strip() or PROTOTYPE_PRIVATE_NETWORK_ID
        normalized_target = target_url.rstrip("/")
        local_targets = {self.modulo_url.rstrip("/")}
        if self.lan_platform_url:
            local_targets.add(self.lan_platform_url.rstrip("/"))
        if normalized_target in local_targets:
            if not self.client.get_status().hosting_enabled:
                self.boot()
            else:
                self._ensure_worker_loop_running()
        body = {
            "model": model_id,
            "buyer_id": buyer_id,
            "scope": "private",
            "private_network_id": network_id,
            "messages": [{"role": "user", "content": user_message}],
            "stream": False,
        }
        req = request.Request(
            f"{target_url.rstrip('/')}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            error_payload = json.loads(exc.read().decode("utf-8")) if exc.fp is not None else {}
            message = error_payload.get("error", str(exc)) if isinstance(error_payload, dict) else str(exc)
            return SmokeTestResult(
                ok=False,
                model_id=model_id,
                user_message=user_message,
                error=message,
                execution_mode="network",
                execution_summary=f"Target: {target_url} | Private network: {network_id}",
            )
        except Exception as exc:
            return SmokeTestResult(
                ok=False,
                model_id=model_id,
                user_message=user_message,
                error=str(exc),
                execution_mode="network",
                execution_summary=f"Target: {target_url} | Private network: {network_id}",
            )

        return SmokeTestResult(
            ok=True,
            model_id=payload.get("model", model_id),
            user_message=user_message,
            response_text=payload.get("message", {}).get("content", ""),
            execution_mode="network",
            execution_summary=f"Target: {target_url} | Private network: {network_id}",
        )

    @staticmethod
    def _discover_lan_ip() -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect(("8.8.8.8", 80))
                ip = sock.getsockname()[0]
            finally:
                sock.close()
        except OSError:
            return ""
        if ip.startswith("127."):
            return ""
        return ip


def main() -> None:
    harness = LocalPrototypeHarness()
    startup_status = harness.boot()
    result = harness.run_round_trip("Hello from the local prototype harness.")

    print("Modulo local prototype booted.")
    print(f"Worker: {startup_status.worker.worker_id if startup_status.worker else 'unknown'}")
    print(f"Model: {result.model_id}")
    print(f"Job: {result.job_id}")
    print(f"User: {result.user_message}")
    print(f"Assistant: {result.response_text}")


if __name__ == "__main__":
    main()
