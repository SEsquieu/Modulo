import json
import threading
import time
import unittest
from pathlib import Path
import sys
from urllib import request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.cloud.http import build_http_server
from modulo.cloud.server import build_server_app
from modulo.common.contracts import RouteScope
from modulo.worker.bridge_runner import build_worker_bridge_runtime


class PrivateNetworkFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service, self.runtime, self.app = build_server_app(
            queued_chat=True,
            chat_wait_timeout_seconds=5.0,
        )
        self.server = build_http_server(
            "127.0.0.1",
            0,
            service=self.service,
            runtime=self.runtime,
            app=self.app,
        )
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2.0)

    def test_cross_machine_style_private_flow_completes_over_http(self) -> None:
        bridge = build_worker_bridge_runtime(
            modulo_url=self.base_url,
            worker_id="remote-worker-1",
            model_id="llama3.1:8b",
            serving_scope=RouteScope.PRIVATE,
            private_network_id="org-a",
            stub_response="hello from remote worker",
        )
        bridge.start()

        stop_event = threading.Event()

        def worker_loop() -> None:
            while not stop_event.is_set():
                bridge.run_cycle()
                time.sleep(0.02)

        worker_thread = threading.Thread(target=worker_loop, daemon=True)
        worker_thread.start()
        try:
            req = request.Request(
                f"{self.base_url}/api/chat",
                data=json.dumps(
                    {
                        "model": "llama3.1:8b",
                        "buyer_id": "buyer-a",
                        "scope": "private",
                        "private_network_id": "org-a",
                        "messages": [{"role": "user", "content": "hello remote path"}],
                        "stream": False,
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=10.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            stop_event.set()
            worker_thread.join(timeout=2.0)
            bridge.stop()

        self.assertEqual("llama3.1:8b", payload["model"])
        self.assertEqual("hello from remote worker", payload["message"]["content"])
        jobs = self.service.jobs.list_jobs()
        self.assertEqual(1, len(jobs))
        self.assertEqual("remote-worker-1", jobs[0].assigned_worker_id)
        trace = self.service.list_traces()[0]
        self.assertEqual(RouteScope.PRIVATE, trace.resolved_scope)
        self.assertEqual("org-a", trace.private_network_id)
        self.assertEqual("completed", trace.final_status)
        self.assertEqual("remote-worker-1", trace.selected_worker_id)


if __name__ == "__main__":
    unittest.main()
