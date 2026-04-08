from __future__ import annotations

from dataclasses import dataclass, field

from modulo.client.app import (
    ActivityEntry,
    ActivityVisibilityStatus,
    ClientSessionBridge,
    ClientStatus,
    ModuloClientSupervisor,
    PlatformModelListing,
    PlatformSessionStatus,
    SmokeTestResult,
)
from modulo.client.ollama_discovery import OllamaDiscovery
from modulo.client.hosting_readiness import OllamaHostingRuntimeProbe
from modulo.cloud.http import ModuloHTTPApp
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService
from modulo.common.catalog import SUPPORTED_MODELS
from modulo.common.contracts import ChatMessage, ChatRequest, ExecutionMode, JobStatus, WorkerBridgeConfig
from modulo.worker.executors import StubExecutor
from modulo.worker.runtime import InMemoryWorkerRuntime, WorkerBridgeRuntime, WorkerExecutor
from modulo.worker.transport import InProcessWorkerHTTPTransport


@dataclass(frozen=True)
class PrototypeRoundTripResult:
    job_id: str
    model_id: str
    buyer_id: str
    assigned_worker_id: str
    user_message: str
    response_text: str
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


@dataclass
class LocalPrototypeHarness:
    model_id: str = "llama3.1:8b"
    worker_id: str = "local-prototype-worker"
    buyer_id: str = "prototype-buyer"
    modulo_url: str = "http://127.0.0.1:8000"
    stub_response_text: str = "Hello from the Modulo local prototype worker."
    executor: WorkerExecutor | None = None
    ollama_discovery: OllamaDiscovery | None = None
    hosting_runtime_probe: OllamaHostingRuntimeProbe | None = None
    service: InMemoryModuloService = field(init=False)
    cloud_runtime: InMemoryWorkerRuntime = field(init=False)
    app: ModuloHTTPApp = field(init=False)
    client: ModuloClientSupervisor = field(init=False)

    def __post_init__(self) -> None:
        self.service = InMemoryModuloService(router=TrustRouter())
        self.cloud_runtime = InMemoryWorkerRuntime()
        self.app = ModuloHTTPApp(service=self.service, runtime=self.cloud_runtime)

        executor = self.executor or StubExecutor()
        if hasattr(executor, "register_worker"):
            executor.register_worker(self.worker_id, self.stub_response_text)

        config = WorkerBridgeConfig(
            modulo_url=self.modulo_url,
            worker_id=self.worker_id,
            enabled_models=(self.model_id,),
        )
        bridge = WorkerBridgeRuntime(
            config=config,
            transport=InProcessWorkerHTTPTransport(app=self.app, config=config),
            executor=executor,
        )
        self.client = ModuloClientSupervisor(
            worker_bridge=bridge,
            session_bridge=LocalPrototypeSessionBridge(service=self.service),
            ollama_discovery=self.ollama_discovery or OllamaDiscovery(),
            hosting_runtime_probe=self.hosting_runtime_probe or OllamaHostingRuntimeProbe(),
            smoke_test_runner=self,
            activity_provider=self,
        )

    def boot(self) -> ClientStatus:
        return self.client.start_hosting()

    def shutdown(self) -> ClientStatus:
        return self.client.stop_hosting()

    def run_round_trip(self, user_message: str, *, buyer_id: str | None = None) -> PrototypeRoundTripResult:
        if not self.client.get_status().hosting_enabled:
            self.boot()

        effective_buyer_id = buyer_id or self.buyer_id
        job = self.service.submit_chat(
            ChatRequest(
                model_id=self.model_id,
                execution_mode=ExecutionMode.NETWORK,
                buyer_id=effective_buyer_id,
                messages=(ChatMessage(role="user", content=user_message),),
            )
        )
        status = self.client.run_hosting_cycle()
        completed_job = self.service.get_job(job.job_id)
        if completed_job is None or not completed_job.response_text:
            raise RuntimeError(f"Prototype job {job.job_id} did not complete successfully")

        return PrototypeRoundTripResult(
            job_id=completed_job.job_id,
            model_id=completed_job.request.model_id,
            buyer_id=effective_buyer_id,
            assigned_worker_id=completed_job.assigned_worker_id,
            user_message=user_message,
            response_text=completed_job.response_text,
            client_status=status,
        )

    def run_smoke_test(self, user_message: str) -> SmokeTestResult:
        try:
            result = self.run_round_trip(user_message)
        except RuntimeError as exc:
            return SmokeTestResult(
                ok=False,
                user_message=user_message,
                error=str(exc),
            )
        return SmokeTestResult(
            ok=True,
            model_id=result.model_id,
            user_message=result.user_message,
            response_text=result.response_text,
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
