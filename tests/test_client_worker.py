import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulo.client.app import ModuloClientSupervisor
from modulo.cloud.router import TrustRouter
from modulo.cloud.runtime import InMemoryModuloService, InMemoryWorkerControlPlane
from modulo.common.contracts import (
    ChatRequest,
    ExecutionMode,
    JobStatus,
    WorkerBridgeConfig,
    WorkerRuntimeState,
)
from modulo.worker.runtime import InMemoryWorkerRuntime, WorkerBridgeRuntime


class ClientWorkerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InMemoryModuloService(router=TrustRouter())
        self.control_plane = InMemoryWorkerControlPlane(service=self.service)
        self.executor = InMemoryWorkerRuntime()
        self.executor.register_worker("worker-1", "hello from worker-1")
        self.bridge = WorkerBridgeRuntime(
            config=WorkerBridgeConfig(
                modulo_url="http://127.0.0.1:8000",
                worker_id="worker-1",
                enabled_models=("llama3.1:8b",),
            ),
            control_plane=self.control_plane,
            executor=self.executor,
        )
        self.client = ModuloClientSupervisor(worker_bridge=self.bridge)

    def test_client_can_start_hosting_without_drifting_from_worker_status(self) -> None:
        status = self.client.start_hosting()
        self.assertTrue(status.hosting_enabled)
        self.assertIsNotNone(status.worker)
        self.assertEqual("worker-1", status.worker.worker_id)
        self.assertTrue(status.worker.registered_with_cloud)
        self.assertEqual(WorkerRuntimeState.IDLE, status.worker.runtime_state)

    def test_worker_cycle_completes_claimed_job_and_updates_client_status(self) -> None:
        self.client.start_hosting()
        job = self.service.submit_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )

        status = self.client.run_hosting_cycle()

        self.assertIsNotNone(status.worker)
        self.assertEqual(JobStatus.COMPLETED, status.worker.last_job_status)
        self.assertEqual(1, status.worker.completed_jobs)

        completed_job = self.service.get_job(job.job_id)
        self.assertIsNotNone(completed_job)
        self.assertEqual(JobStatus.COMPLETED, completed_job.status)
        self.assertEqual("hello from worker-1", completed_job.response_text)

    def test_worker_failure_surfaces_through_shared_status_contract(self) -> None:
        self.bridge = WorkerBridgeRuntime(
            config=WorkerBridgeConfig(
                modulo_url="http://127.0.0.1:8000",
                worker_id="worker-2",
                enabled_models=("llama3.1:8b",),
            ),
            control_plane=self.control_plane,
            executor=InMemoryWorkerRuntime(),
        )
        self.client = ModuloClientSupervisor(worker_bridge=self.bridge)
        self.client.start_hosting()

        job = self.service.submit_chat(
            ChatRequest(model_id="llama3.1:8b", execution_mode=ExecutionMode.NETWORK)
        )
        status = self.client.run_hosting_cycle()

        self.assertIsNotNone(status.worker)
        self.assertEqual(WorkerRuntimeState.ERROR, status.worker.runtime_state)
        self.assertEqual(JobStatus.FAILED, status.worker.last_job_status)
        self.assertEqual(1, status.worker.failed_jobs)
        self.assertIn("No execution adapter", status.worker.last_error)

        failed_job = self.service.get_job(job.job_id)
        self.assertIsNotNone(failed_job)
        self.assertEqual(JobStatus.FAILED, failed_job.status)


if __name__ == "__main__":
    unittest.main()
