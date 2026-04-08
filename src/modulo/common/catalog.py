from __future__ import annotations

from modulo.common.contracts import CanonicalModel


SUPPORTED_MODELS: dict[str, CanonicalModel] = {
    "llama3.1:8b": CanonicalModel(
        model_id="llama3.1:8b",
        ollama_runtime_name="llama3.1:8b",
        display_name="Llama 3.1 8B",
        canonical_model_identity="llama3.1:8b",
        supports_tools=False,
        supports_streaming=False,
    ),
}


def get_model(model_id: str) -> CanonicalModel | None:
    return SUPPORTED_MODELS.get(model_id)

