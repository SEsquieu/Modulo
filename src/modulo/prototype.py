from __future__ import annotations

from dataclasses import dataclass, field

from modulo.client.app import ClientStatus, ModuloClientSupervisor, SmokeTestResult
from modulo.cloud.http import ModuloHTTPApp
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService
from modulo.common.contracts import ChatMessage, ChatRequest, ExecutionMode, WorkerBridgeConfig
from modulo.worker.executors import StubExecutor
from modulo.worker.runtime import InMemoryWorkerRuntime, WorkerBridgeRuntime, WorkerExecutor
from modulo.worker.transport import InProcessWorkerHTTPTransport


@dataclass(frozen=True)
class PrototypeRoundTripResult:
    job_id: str
    model_id: str
    user_message: str
    response_text: str
    client_status: ClientStatus


@dataclass
class LocalPrototypeHarness:
    model_id: str = "llama3.1:8b"
    worker_id: str = "local-prototype-worker"
    modulo_url: str = "http://127.0.0.1:8000"
    stub_response_text: str = "Hello from the Modulo local prototype worker."
    executor: WorkerExecutor | None = None
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
        self.client = ModuloClientSupervisor(worker_bridge=bridge, smoke_test_runner=self)

    def boot(self) -> ClientStatus:
        self.client.connect_openclaw()
        return self.client.start_hosting()

    def shutdown(self) -> ClientStatus:
        return self.client.stop_hosting()

    def run_round_trip(self, user_message: str) -> PrototypeRoundTripResult:
        if not self.client.get_status().hosting_enabled:
            self.boot()

        job = self.service.submit_chat(
            ChatRequest(
                model_id=self.model_id,
                execution_mode=ExecutionMode.NETWORK,
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
