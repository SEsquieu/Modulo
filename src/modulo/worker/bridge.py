from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerBridgeConfig:
    modulo_url: str
    worker_id: str
    enabled_models: tuple[str, ...]
    max_concurrency: int = 1


def describe_worker_responsibilities() -> list[str]:
    """Summarize the responsibilities of the future worker bridge."""
    return [
        "register with the Modulo cloud control plane",
        "heartbeat health and current load",
        "claim jobs when capacity is available",
        "execute requests against local Ollama",
        "report results or failures back to the cloud",
    ]
