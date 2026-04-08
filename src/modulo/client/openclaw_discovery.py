from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil


@dataclass(frozen=True)
class OpenClawDiscoveryStatus:
    installed: bool = False
    config_present: bool = False
    configured_for_modulo: bool = False
    state: str = "not_installed"
    summary: str = "OpenClaw was not detected on this machine."
    details: str = "No OpenClaw install or config footprint was found."
    config_path: str = ""
    current_provider: str = ""
    current_primary_model: str = ""
    current_base_url: str = ""
    error: str = ""


class OpenClawDiscovery:
    def __init__(
        self,
        *,
        modulo_url: str,
        config_path: Path | None = None,
        detect_command: bool = True,
    ) -> None:
        self.modulo_url = modulo_url.rstrip("/")
        self.config_path = config_path or (Path.home() / ".openclaw" / "openclaw.json")
        self.detect_command = detect_command

    def discover(self) -> OpenClawDiscoveryStatus:
        command_path = None
        if self.detect_command:
            command_path = shutil.which("openclaw") or shutil.which("openclaw.ps1")
        config_exists = self.config_path.exists()
        installed = bool(command_path) or config_exists
        if not installed:
            return OpenClawDiscoveryStatus()

        if not config_exists:
            return OpenClawDiscoveryStatus(
                installed=True,
                config_present=False,
                state="installed_unconfigured",
                summary="OpenClaw is installed, but no local config file was found.",
                details=(
                    "The OpenClaw command is available, but the standard config file was not found "
                    f"at {self.config_path}."
                ),
                config_path=str(self.config_path),
            )

        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return OpenClawDiscoveryStatus(
                installed=True,
                config_present=True,
                state="installed_unconfigured",
                summary="OpenClaw config was found, but it could not be read cleanly.",
                details=f"Config path: {self.config_path}",
                config_path=str(self.config_path),
                error=str(exc),
            )

        primary_model = str(payload.get("model", {}).get("primary", ""))
        current_provider = primary_model.split("/", 1)[0] if "/" in primary_model else ""
        provider_config = payload.get("models", {}).get("providers", {}).get(current_provider, {})
        if not isinstance(provider_config, dict):
            provider_config = {}
        base_url = str(provider_config.get("baseUrl", "")).rstrip("/")
        configured_for_modulo = bool(base_url) and base_url == self.modulo_url

        if configured_for_modulo:
            summary = "OpenClaw is installed and configured to route through Modulo."
            state = "configured"
        else:
            summary = "OpenClaw is installed, but the local config is not routing through Modulo."
            state = "installed_unconfigured"

        details_lines = [
            f"Config path: {self.config_path}",
            f"Primary model: {primary_model or 'None'}",
            f"Provider: {current_provider or 'Unknown'}",
            f"Base URL: {base_url or 'Unknown'}",
        ]
        return OpenClawDiscoveryStatus(
            installed=True,
            config_present=True,
            configured_for_modulo=configured_for_modulo,
            state=state,
            summary=summary,
            details="\n".join(details_lines),
            config_path=str(self.config_path),
            current_provider=current_provider,
            current_primary_model=primary_model,
            current_base_url=base_url,
        )
