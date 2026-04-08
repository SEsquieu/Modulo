from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True)
class HostingRuntimeProbeStatus:
    reachable: bool = False
    model_ready: bool = False
    summary: str = "Ollama runtime has not been probed."
    detail: str = ""
    error: str = ""


class OllamaHostingRuntimeProbe:
    """Run lightweight local runtime checks for a selected Ollama model."""

    def probe(self, model_id: str) -> HostingRuntimeProbeStatus:
        try:
            completed = subprocess.run(
                ["ollama", "show", model_id],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except FileNotFoundError:
            return HostingRuntimeProbeStatus(
                reachable=False,
                model_ready=False,
                summary="Ollama runtime command is not available.",
                detail="Install Ollama locally before hosting can be enabled.",
                error="ollama command not found",
            )
        except subprocess.TimeoutExpired:
            return HostingRuntimeProbeStatus(
                reachable=False,
                model_ready=False,
                summary="Ollama runtime did not respond in time.",
                detail="The local runtime probe timed out while checking the selected model.",
                error="ollama show timed out",
            )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            error = stderr or stdout or f"ollama show exited with code {completed.returncode}"
            return HostingRuntimeProbeStatus(
                reachable=False,
                model_ready=False,
                summary="Ollama runtime could not resolve the selected model.",
                detail=error,
                error=error,
            )

        return HostingRuntimeProbeStatus(
            reachable=True,
            model_ready=True,
            summary=f"Ollama runtime resolved {model_id} successfully.",
            detail="The local runtime responded to the selected model check.",
        )
