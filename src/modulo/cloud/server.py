from __future__ import annotations

import argparse

from modulo.cloud.http import ModuloHTTPApp, build_http_server
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService
from modulo.worker.runtime import InMemoryWorkerRuntime


def build_server_app(
    *,
    queued_chat: bool = True,
    chat_wait_timeout_seconds: float = 30.0,
) -> tuple[InMemoryModuloService, InMemoryWorkerRuntime, ModuloHTTPApp]:
    service = InMemoryModuloService(router=TrustRouter())
    runtime = InMemoryWorkerRuntime()
    app = ModuloHTTPApp(
        service=service,
        runtime=runtime,
        inline_chat_execution=not queued_chat,
        chat_wait_timeout_seconds=chat_wait_timeout_seconds,
        chat_wait_poll_seconds=0.05,
    )
    return service, runtime, app


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Modulo control-plane HTTP server for private-network testing."
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--inline-chat-execution",
        action="store_true",
        help="Execute /api/chat inline instead of queued worker execution.",
    )
    parser.add_argument("--chat-wait-timeout", type=float, default=30.0)
    args = parser.parse_args()

    service, runtime, app = build_server_app(
        queued_chat=not args.inline_chat_execution,
        chat_wait_timeout_seconds=args.chat_wait_timeout,
    )
    server = build_http_server(
        args.host,
        args.port,
        service=service,
        runtime=runtime,
        app=app,
    )
    print(f"Modulo control plane listening on http://{args.host}:{args.port}")
    if app.inline_chat_execution:
        print("Chat mode: inline execution")
    else:
        print("Chat mode: queued worker execution")
    server.serve_forever()


if __name__ == "__main__":
    main()
