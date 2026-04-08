from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True)
class OllamaDiscoveryStatus:
    available: bool = False
    command_path: str = "ollama"
    installed_model_ids: tuple[str, ...] = ()
    summary: str = "Ollama is not available."
    details: str = "Modulo could not detect a local Ollama installation yet."
    error: str = ""


class OllamaDiscovery:
    """Detect local Ollama availability and installed models."""

    def discover(self) -> OllamaDiscoveryStatus:
        try:
            completed = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except FileNotFoundError:
            return OllamaDiscoveryStatus(
                available=False,
                summary="Ollama is not installed or is not on PATH.",
                details="Install Ollama locally before Modulo can discover hostable models.",
                error="ollama command not found",
            )
        except subprocess.TimeoutExpired:
            return OllamaDiscoveryStatus(
                available=False,
                summary="Ollama did not respond in time.",
                details="The local Ollama command timed out during discovery.",
                error="ollama list timed out",
            )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            error = stderr or stdout or f"ollama list exited with code {completed.returncode}"
            return OllamaDiscoveryStatus(
                available=False,
                summary="Ollama is installed but did not respond successfully.",
                details=error,
                error=error,
            )

        models = self._parse_models(stdout)
        if models:
            return OllamaDiscoveryStatus(
                available=True,
                installed_model_ids=models,
                summary=f"Ollama is available with {len(models)} local model(s).",
                details="Modulo can inspect the local Ollama inventory.",
            )
        return OllamaDiscoveryStatus(
            available=True,
            installed_model_ids=(),
            summary="Ollama is available, but no local models were found.",
            details="Pull a supported model locally before enabling hosting.",
        )

    @staticmethod
    def _parse_models(output: str) -> tuple[str, ...]:
        if not output:
            return ()
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return ()
        if lines[0].upper().startswith("NAME"):
            lines = lines[1:]

        model_ids: list[str] = []
        for line in lines:
            first_token = line.split()[0]
            if first_token and first_token not in model_ids:
                model_ids.append(first_token)
        return tuple(model_ids)
