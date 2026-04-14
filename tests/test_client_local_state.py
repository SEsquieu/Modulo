import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.client.app import ClientLocalStateStatus, ModuloClientSupervisor
from modulo.client.local_state import ClientLocalStateResolver
from modulo.cloud.http import ModuloHTTPApp
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService
from modulo.common.contracts import WorkerBridgeConfig
from modulo.worker.executors import StubExecutor
from modulo.worker.runtime import InMemoryWorkerRuntime
from modulo.worker.runtime import WorkerBridgeRuntime
from modulo.worker.transport import InProcessWorkerHTTPTransport


class ClientLocalStateResolverTests(unittest.TestCase):
    def test_resolver_defaults_to_dot_modulo_under_home(self) -> None:
        resolver = ClientLocalStateResolver(home_path=Path("C:/Users/tester"))

        paths = resolver.resolve()

        self.assertEqual("C:\\Users\\tester\\.modulo", paths.root_path)
        self.assertEqual("C:\\Users\\tester\\.modulo\\backups", paths.backups_path)
        self.assertEqual("C:\\Users\\tester\\.modulo\\mounts", paths.mounts_path)
        self.assertEqual("C:\\Users\\tester\\.modulo\\telemetry", paths.telemetry_path)
        self.assertEqual("C:\\Users\\tester\\.modulo\\state.json", paths.manifest_path)

    def test_resolver_preserves_explicit_root_override(self) -> None:
        resolver = ClientLocalStateResolver(root_path=Path("D:/ModuloState"))

        paths = resolver.resolve()

        self.assertEqual("D:\\ModuloState", paths.root_path)
        self.assertEqual("D:\\ModuloState\\backups", paths.backups_path)
        self.assertEqual("D:\\ModuloState\\mounts", paths.mounts_path)
        self.assertEqual("D:\\ModuloState\\telemetry", paths.telemetry_path)
        self.assertEqual("D:\\ModuloState\\state.json", paths.manifest_path)


class ClientLocalStateStatusTests(unittest.TestCase):
    def test_status_summarizes_reserved_client_state_paths(self) -> None:
        status = ClientLocalStateStatus.from_paths(
            ClientLocalStateResolver(home_path=Path("C:/Users/tester")).resolve()
        )

        self.assertIn("reserved", status.summary.lower())
        self.assertIn("Root: C:\\Users\\tester\\.modulo", status.details)
        self.assertIn("Backups: C:\\Users\\tester\\.modulo\\backups", status.details)

    def test_client_status_carries_local_state_contract(self) -> None:
        service = InMemoryModuloService(router=TrustRouter())
        app = ModuloHTTPApp(service=service, runtime=InMemoryWorkerRuntime())
        transport = InProcessWorkerHTTPTransport(
            app=app,
            config=WorkerBridgeConfig(
                modulo_url="http://127.0.0.1:8000",
                worker_id="worker-local-state",
                enabled_models=("llama3.1:8b",),
            ),
        )
        bridge = WorkerBridgeRuntime(
            config=transport.config,
            transport=transport,
            executor=StubExecutor(),
        )
        client = ModuloClientSupervisor(
            worker_bridge=bridge,
            local_state_resolver=ClientLocalStateResolver(
                root_path=Path("C:/Users/tester/.modulo")
            ),
        )

        status = client.get_status()

        self.assertEqual("C:\\Users\\tester\\.modulo", status.client_local_state.root_path)
        self.assertEqual(
            "C:\\Users\\tester\\.modulo\\backups",
            status.client_local_state.backups_path,
        )
        self.assertEqual(
            "C:\\Users\\tester\\.modulo\\mounts",
            status.client_local_state.mounts_path,
        )
        self.assertEqual(
            "C:\\Users\\tester\\.modulo\\telemetry",
            status.client_local_state.telemetry_path,
        )


if __name__ == "__main__":
    unittest.main()
