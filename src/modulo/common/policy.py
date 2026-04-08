from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class V1Policy:
    exact_model_match_only: bool = True
    allow_model_substitution: bool = False
    allow_cross_mode_fallback: bool = False
    allow_trusted_cloud_fallback_for_exact_match: bool = True
    require_curated_supported_model: bool = True
    streaming_enabled: bool = False
    tool_calling_enabled: bool = False
    allow_cpu_only_workers: bool = False
    max_supported_models_in_happy_path: int = 3


V1_DEFAULT_POLICY = V1Policy()

