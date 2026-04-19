from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExecutionMode(str, Enum):
    LOCAL = "local"
    NETWORK = "network"
    CLOUD = "cloud"


class RouteScope(str, Enum):
    LOCAL = "local"
    PRIVATE = "private"
    PUBLIC = "public"
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


class WorkerRuntimeState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


class WorkerSupervisorCommand(str, Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"


class ChatStreamEventType(str, Enum):
    START = "start"
    TOKEN = "token"
    END = "end"
    ERROR = "error"


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
    serving_scope: RouteScope | None = None
    private_network_id: str = ""
    trust_notes: tuple[str, ...] = field(default_factory=tuple)

    def supports_model(self, model_id: str) -> WorkerModelState | None:
        for state in self.advertised_models:
            if state.model_id == model_id:
                return state
        return None

    def resolved_scope(self) -> RouteScope:
        if self.serving_scope is not None:
            return self.serving_scope
        return {
            WorkerKind.LOCAL: RouteScope.LOCAL,
            WorkerKind.NETWORK: RouteScope.PRIVATE,
            WorkerKind.CLOUD: RouteScope.CLOUD,
        }[self.kind]


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatRequest:
    model_id: str
    execution_mode: ExecutionMode
    buyer_id: str = ""
    messages: tuple[ChatMessage, ...] = field(default_factory=tuple)
    routing_policy: RoutingPolicy = RoutingPolicy.STRICT
    stream: bool = False
    requires_tools: bool = False
    requested_scope: RouteScope | None = None
    private_network_id: str = ""

    def resolved_scope(self) -> RouteScope:
        if self.requested_scope is not None:
            return self.requested_scope
        return {
            ExecutionMode.LOCAL: RouteScope.LOCAL,
            ExecutionMode.NETWORK: RouteScope.PRIVATE,
            ExecutionMode.CLOUD: RouteScope.CLOUD,
        }[self.execution_mode]


@dataclass(frozen=True)
class ChatStreamEvent:
    event_type: ChatStreamEventType
    content: str = ""
    model_id: str = ""
    error: str = ""


@dataclass(frozen=True)
class RouteDecision:
    worker_id: str
    worker_kind: WorkerKind
    model_id: str
    execution_mode: ExecutionMode
    routed_via_fallback: bool = False
    reason: str = ""


@dataclass(frozen=True)
class FilteredWorkerReason:
    worker_id: str
    reason_code: str
    detail: str = ""


@dataclass(frozen=True)
class RouteTraceRecord:
    trace_id: str
    model_id: str
    buyer_id: str
    selected_source: str
    resolved_scope: RouteScope
    private_network_id: str = ""
    requested_execution_mode: ExecutionMode = ExecutionMode.NETWORK
    job_id: str = ""
    attempt_number: int = 1
    retry_count: int = 0
    eligible_worker_ids: tuple[str, ...] = field(default_factory=tuple)
    filtered_worker_reasons: tuple[FilteredWorkerReason, ...] = field(default_factory=tuple)
    selected_worker_id: str = ""
    selected_worker_kind: WorkerKind | None = None
    route_reason: str = ""
    route_reason_code: str = ""
    continuity_used: bool = False
    warm_path_used: bool = False
    current_status: str = "selected"
    final_status: str = ""
    final_error: str = ""
    created_at_tick: int = 0
    updated_at_tick: int = 0


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    request: ChatRequest
    status: JobStatus
    route: RouteDecision
    assigned_worker_id: str
    assigned_worker_kind: WorkerKind
    trace_id: str = ""
    attempts: int = 1
    failure_reason: str = ""
    response_text: str = ""


@dataclass(frozen=True)
class JobClaim:
    job_id: str
    worker_id: str
    request: ChatRequest
    route: RouteDecision
    trace_id: str = ""


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


@dataclass(frozen=True)
class WorkerHeartbeat:
    worker_id: str
    healthy: bool
    current_load: int = 0


@dataclass(frozen=True)
class WorkerBridgeConfig:
    modulo_url: str
    worker_id: str
    enabled_models: tuple[str, ...]
    max_concurrency: int = 1
    kind: WorkerKind = WorkerKind.NETWORK
    serving_scope: RouteScope | None = None
    private_network_id: str = ""


@dataclass(frozen=True)
class WorkerStatusSnapshot:
    worker_id: str
    desired_running: bool = False
    runtime_state: WorkerRuntimeState = WorkerRuntimeState.STOPPED
    registered_with_cloud: bool = False
    healthy: bool = False
    current_load: int = 0
    enabled_models: tuple[str, ...] = field(default_factory=tuple)
    last_job_id: str = ""
    last_job_status: JobStatus | None = None
    last_error: str = ""
    completed_jobs: int = 0
    failed_jobs: int = 0
