from __future__ import annotations

import argparse
import time

from modulo.client.hosting_readiness import OllamaHostingRuntimeProbe
from modulo.common.contracts import RouteScope, WorkerBridgeConfig
from modulo.worker.executors import OllamaExecutor, StubExecutor, UrllibOllamaHTTPClient
from modulo.worker.runtime import WorkerBridgeRuntime, WorkerExecutor
from modulo.worker.transport import UrllibWorkerHTTPTransport


def build_worker_bridge_runtime(
    *,
    modulo_url: str,
    worker_id: str,
    model_id: str,
    serving_scope: RouteScope = RouteScope.PRIVATE,
    private_network_id: str = "",
    max_concurrency: int = 1,
    ollama_base_url: str = "http://127.0.0.1:11434",
    ollama_timeout_seconds: float = 120.0,
    stub_response: str = "",
) -> WorkerBridgeRuntime:
    config = WorkerBridgeConfig(
        modulo_url=modulo_url,
        worker_id=worker_id,
        enabled_models=(model_id,),
        max_concurrency=max_concurrency,
        serving_scope=serving_scope,
        private_network_id=private_network_id,
    )
    transport = UrllibWorkerHTTPTransport(config=config)
    executor = _build_executor(
        worker_id=worker_id,
        model_id=model_id,
        ollama_base_url=ollama_base_url,
        ollama_timeout_seconds=ollama_timeout_seconds,
        stub_response=stub_response,
    )
    return WorkerBridgeRuntime(
        config=config,
        transport=transport,
        executor=executor,
    )


def _build_executor(
    *,
    worker_id: str,
    model_id: str,
    ollama_base_url: str,
    ollama_timeout_seconds: float,
    stub_response: str,
) -> WorkerExecutor:
    if stub_response:
        executor = StubExecutor()
        executor.register_worker(worker_id, stub_response)
        return executor

    probe = OllamaHostingRuntimeProbe(base_url=ollama_base_url)
    probe_status = probe.probe(model_id)
    if not probe_status.reachable or not probe_status.model_ready:
        raise RuntimeError(
            "Worker runtime probe did not pass. "
            f"Model {model_id} is not ready at {ollama_base_url}. "
            f"Detail: {probe_status.detail or probe_status.summary}"
        )

    return OllamaExecutor(
        base_url=ollama_base_url,
        http_client=UrllibOllamaHTTPClient(timeout_seconds=ollama_timeout_seconds),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a Modulo worker bridge against a remote control-plane endpoint."
    )
    parser.add_argument("--modulo-url", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--scope", choices=[scope.value for scope in RouteScope], default="private")
    parser.add_argument("--private-network-id", default="")
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--ollama-base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-timeout", type=float, default=120.0)
    parser.add_argument("--poll-interval", type=float, default=0.25)
    parser.add_argument(
        "--stub-response",
        default="",
        help="Use a stub executor instead of a real Ollama-backed executor.",
    )
    args = parser.parse_args()

    bridge = build_worker_bridge_runtime(
        modulo_url=args.modulo_url,
        worker_id=args.worker_id,
        model_id=args.model,
        serving_scope=RouteScope(args.scope),
        private_network_id=args.private_network_id,
        max_concurrency=args.max_concurrency,
        ollama_base_url=args.ollama_base_url,
        ollama_timeout_seconds=args.ollama_timeout,
        stub_response=args.stub_response,
    )

    status = bridge.start()
    print(
        f"Modulo worker bridge started for {args.worker_id} on {args.modulo_url} "
        f"with model {args.model}."
    )
    print(f"Initial state: {status.runtime_state.value}")
    try:
        while True:
            status = bridge.run_cycle()
            time.sleep(args.poll_interval)
            if status.runtime_state.value == "error":
                print(f"Worker entered error state: {status.last_error}")
    except KeyboardInterrupt:
        stopped = bridge.stop()
        print(f"Modulo worker bridge stopped with state {stopped.runtime_state.value}.")


if __name__ == "__main__":
    main()
