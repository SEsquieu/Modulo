from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContinueDiscoveryStatus:
    config_present: bool = False
    configured_for_modulo: bool = False
    managed_entry_present: bool = False
    state: str = "missing_config"
    summary: str = "Continue config was not detected on this machine yet."
    details: str = "Modulo has not found a local Continue config file."
    config_path: str = ""
    error: str = ""


class ContinueDiscovery:
    def __init__(
        self,
        *,
        modulo_url: str,
        config_path: Path | None = None,
        managed_marker: str = "# modulo-managed-continue",
    ) -> None:
        self.modulo_url = modulo_url.rstrip("/")
        self.config_path = config_path or (Path.home() / ".continue" / "config.yaml")
        self.managed_marker = managed_marker

    def discover(self) -> ContinueDiscoveryStatus:
        if not self.config_path.exists():
            return ContinueDiscoveryStatus(
                config_present=False,
                state="missing_config",
                summary="Continue config was not detected on this machine yet.",
                details=(
                    "Modulo did not find a Continue config file at "
                    f"{self.config_path}. A future apply flow can create or update it safely."
                ),
                config_path=str(self.config_path),
            )

        try:
            content = self.config_path.read_text(encoding="utf-8")
        except OSError as exc:
            return ContinueDiscoveryStatus(
                config_present=True,
                state="read_error",
                summary="Continue config was found, but it could not be read cleanly.",
                details=f"Config path: {self.config_path}\nRead error: {exc}",
                config_path=str(self.config_path),
                error=str(exc),
            )

        normalized_content = content.rstrip()
        managed_entry_present = self.managed_marker in normalized_content
        configured_for_modulo = self.modulo_url in normalized_content
        state = (
            "configured"
            if configured_for_modulo and managed_entry_present
            else "configured_external"
            if configured_for_modulo
            else "detected_unconfigured"
        )
        summary = (
            "Continue config appears to include a Modulo-managed entry."
            if configured_for_modulo and managed_entry_present
            else "Continue config appears to point at Modulo, but not through a managed Modulo block."
            if configured_for_modulo
            else "Continue config is present, but it does not appear to point at Modulo yet."
        )
        details = [
            f"Config path: {self.config_path}",
            f"Modulo URL detected: {'yes' if configured_for_modulo else 'no'}",
            f"Managed Modulo marker detected: {'yes' if managed_entry_present else 'no'}",
        ]
        return ContinueDiscoveryStatus(
            config_present=True,
            configured_for_modulo=configured_for_modulo,
            managed_entry_present=managed_entry_present,
            state=state,
            summary=summary,
            details="\n".join(details),
            config_path=str(self.config_path),
        )
