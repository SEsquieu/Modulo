from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExecutionMode(str, Enum):
    LOCAL = "local"
    NETWORK = "network"
    CLOUD = "cloud"


class RoutingPolicy(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    ECONOMY = "economy"


class WorkerKind(str, Enum):
    NETWORK = "network"
    CLOUD = "cloud"
    LOCAL = "local"


class JobStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class CanonicalModel:
    model_id: str
    ollama_runtime_name: str
    display_name: str
    canonical_model_identity: str
    supports_tools: bool = False
    supports_streaming: bool = False


@dataclass(frozen=True)
class WorkerModelState:
    model_id: str
    runtime_identity: str
    current_load: int = 0
    recent_success_rate: float = 1.0
    timeout_rate: float = 0.0
    confidence: float = 1.0


@dataclass(frozen=True)
class WorkerSnapshot:
    worker_id: str
    kind: WorkerKind
    healthy: bool
    max_concurrency: int
    advertised_models: tuple[WorkerModelState, ...]
    trust_notes: tuple[str, ...] = field(default_factory=tuple)

    def supports_model(self, model_id: str) -> WorkerModelState | None:
        for state in self.advertised_models:
            if state.model_id == model_id:
                return state
        return None


@dataclass(frozen=True)
class ChatRequest:
    model_id: str
    execution_mode: ExecutionMode
    routing_policy: RoutingPolicy = RoutingPolicy.STRICT
    stream: bool = False
    requires_tools: bool = False


@dataclass(frozen=True)
class RouteDecision:
    worker_id: str
    worker_kind: WorkerKind
    model_id: str
    execution_mode: ExecutionMode
    routed_via_fallback: bool = False
    reason: str = ""


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    request: ChatRequest
    status: JobStatus
    route: RouteDecision
    assigned_worker_id: str
    assigned_worker_kind: WorkerKind
    attempts: int = 1
    failure_reason: str = ""
    response_text: str = ""


@dataclass(frozen=True)
class JobClaim:
    job_id: str
    worker_id: str
    request: ChatRequest
    route: RouteDecision


@dataclass(frozen=True)
class JobResult:
    job_id: str
    worker_id: str
    response_text: str


@dataclass(frozen=True)
class JobFailure:
    job_id: str
    worker_id: str
    error_code: str
    message: str
