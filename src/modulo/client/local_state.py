from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClientLocalStatePaths:
    root_path: str
    backups_path: str
    mounts_path: str
    telemetry_path: str
    telemetry_events_path: str
    telemetry_mount_events_path: str
    telemetry_recovery_events_path: str
    manifest_path: str


class ClientLocalStateResolver:
    def __init__(
        self,
        *,
        root_path: Path | None = None,
        home_path: Path | None = None,
    ) -> None:
        self._explicit_root = root_path
        self._home_path = home_path

    def resolve(self) -> ClientLocalStatePaths:
        root = self._resolve_root_path()
        return ClientLocalStatePaths(
            root_path=str(root),
            backups_path=str(root / "backups"),
            mounts_path=str(root / "mounts"),
            telemetry_path=str(root / "telemetry"),
            telemetry_events_path=str(root / "telemetry" / "events.jsonl"),
            telemetry_mount_events_path=str(root / "telemetry" / "mounts.jsonl"),
            telemetry_recovery_events_path=str(root / "telemetry" / "recovery.jsonl"),
            manifest_path=str(root / "state.json"),
        )

    def _resolve_root_path(self) -> Path:
        if self._explicit_root is not None:
            return self._explicit_root
        home = self._home_path or Path.home()
        return home / ".modulo"
