from __future__ import annotations

from modulo.common.contracts import WorkerKind, WorkerModelState, WorkerSnapshot
from modulo.cloud.http import build_http_server
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService
from modulo.worker.runtime import InMemoryWorkerRuntime


def main() -> None:
    service = InMemoryModuloService(router=TrustRouter())
    runtime = InMemoryWorkerRuntime()

    service.register_worker(
        WorkerSnapshot(
            worker_id="network-demo-1",
            kind=WorkerKind.NETWORK,
            healthy=True,
            max_concurrency=1,
            advertised_models=(
                WorkerModelState(
                    model_id="llama3.1:8b",
                    runtime_identity="llama3.1:8b",
                ),
            ),
        )
    )
    runtime.register_worker("network-demo-1", "Hello from the Modulo demo worker.")

    server = build_http_server("127.0.0.1", 8000, service=service, runtime=runtime)
    print("Modulo demo server listening on http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
