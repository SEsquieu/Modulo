from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, request


@dataclass(frozen=True)
class LoadedOllamaModel:
    model_id: str
    display_name: str
    expires_at: str = ""
    size_bytes: int = 0
    size_vram_bytes: int = 0
    context_length: int = 0
    family: str = ""
    parameter_size: str = ""
    quantization_level: str = ""


@dataclass(frozen=True)
class OllamaLoadedModelsStatus:
    available: bool = False
    loaded_models: tuple[LoadedOllamaModel, ...] = ()
    summary: str = "No Ollama loaded-model state is available."
    details: str = "Modulo has not checked which Ollama models are currently loaded."
    error: str = ""


@dataclass(frozen=True)
class OllamaLoadedModelsDiscovery:
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 5.0

    def discover(self) -> OllamaLoadedModelsStatus:
        endpoint = f"{self.base_url.rstrip('/')}/api/ps"
        req = request.Request(endpoint, method="GET")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            return OllamaLoadedModelsStatus(
                available=False,
                summary="Ollama loaded-model state is unavailable.",
                details=f"Modulo could not query the local Ollama runtime at {endpoint}.",
                error=str(reason),
            )
        except TimeoutError:
            return OllamaLoadedModelsStatus(
                available=False,
                summary="Ollama loaded-model check timed out.",
                details="The local Ollama runtime did not respond in time to a loaded-model check.",
                error="ollama ps timed out",
            )

        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            return OllamaLoadedModelsStatus(
                available=False,
                summary="Ollama returned invalid loaded-model data.",
                details="The local Ollama runtime returned invalid JSON for /api/ps.",
                error="invalid ollama ps json",
            )

        models_raw = payload.get("models", [])
        if not isinstance(models_raw, list):
            return OllamaLoadedModelsStatus(
                available=False,
                summary="Ollama returned an unexpected loaded-model payload.",
                details="The local Ollama runtime did not return a model list for /api/ps.",
                error="invalid ollama ps payload",
            )

        loaded_models: list[LoadedOllamaModel] = []
        for item in models_raw:
            if not isinstance(item, dict):
                continue
            model_id = item.get("model") or item.get("name")
            if not isinstance(model_id, str) or not model_id:
                continue
            details = item.get("details", {})
            if not isinstance(details, dict):
                details = {}
            loaded_models.append(
                LoadedOllamaModel(
                    model_id=model_id,
                    display_name=str(item.get("name") or model_id),
                    expires_at=str(item.get("expires_at") or ""),
                    size_bytes=_int_value(item.get("size")),
                    size_vram_bytes=_int_value(item.get("size_vram")),
                    context_length=_int_value(item.get("context_length")),
                    family=str(details.get("family") or ""),
                    parameter_size=str(details.get("parameter_size") or ""),
                    quantization_level=str(details.get("quantization_level") or ""),
                )
            )

        if loaded_models:
            return OllamaLoadedModelsStatus(
                available=True,
                loaded_models=tuple(loaded_models),
                summary=f"{len(loaded_models)} Ollama model(s) are currently loaded in memory.",
                details="Modulo can inspect the current loaded-model state from the local Ollama runtime.",
            )
        return OllamaLoadedModelsStatus(
            available=True,
            loaded_models=(),
            summary="No Ollama models are currently loaded in memory.",
            details="The local Ollama runtime is reachable, but no models are currently loaded.",
        )


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    return 0
