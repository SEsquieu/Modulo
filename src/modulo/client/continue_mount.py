from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re


MANAGED_BLOCK_START = "# modulo-managed-continue:start"
MANAGED_BLOCK_END = "# modulo-managed-continue:end"


@dataclass(frozen=True)
class ContinueMountMetadata:
    config_path: str
    backup_path: str
    rollback_metadata_path: str
    had_existing_config: bool
    created_config: bool
    model_id: str
    model_name: str
    api_base: str
    applied_at: str


@dataclass(frozen=True)
class ContinueMountApplyResult:
    ok: bool
    summary: str
    detail: str = ""


class ContinueMountManager:
    def __init__(
        self,
        *,
        config_path: Path,
        backup_path: Path,
        rollback_metadata_path: Path,
        api_base: str,
    ) -> None:
        self.config_path = config_path
        self.backup_path = backup_path
        self.rollback_metadata_path = rollback_metadata_path
        self.api_base = api_base.rstrip("/")

    def apply(self, *, model_id: str, model_name: str) -> ContinueMountApplyResult:
        existing_content = ""
        had_existing_config = self.config_path.exists()
        if had_existing_config:
            existing_content = self.config_path.read_text(encoding="utf-8")

        self._ensure_parent_dirs()
        self.backup_path.write_text(existing_content, encoding="utf-8")

        updated = self._updated_config_content(
            existing_content,
            model_id=model_id,
            model_name=model_name,
        )
        self.config_path.write_text(updated, encoding="utf-8")

        metadata = ContinueMountMetadata(
            config_path=str(self.config_path),
            backup_path=str(self.backup_path),
            rollback_metadata_path=str(self.rollback_metadata_path),
            had_existing_config=had_existing_config,
            created_config=not had_existing_config,
            model_id=model_id,
            model_name=model_name,
            api_base=self.api_base,
            applied_at=datetime.now(timezone.utc).isoformat(),
        )
        self.rollback_metadata_path.write_text(
            json.dumps(asdict(metadata), indent=2),
            encoding="utf-8",
        )
        return ContinueMountApplyResult(
            ok=True,
            summary="Continue mount was applied successfully.",
            detail=(
                f"Config: {self.config_path}\n"
                f"Backup: {self.backup_path}\n"
                f"Rollback metadata: {self.rollback_metadata_path}"
            ),
        )

    def rollback(self) -> ContinueMountApplyResult:
        if not self.rollback_metadata_path.exists():
            return ContinueMountApplyResult(
                ok=False,
                summary="Continue rollback metadata was not found.",
                detail=str(self.rollback_metadata_path),
            )

        metadata = ContinueMountMetadata(**json.loads(self.rollback_metadata_path.read_text(encoding="utf-8")))
        backup_content = ""
        if self.backup_path.exists():
            backup_content = self.backup_path.read_text(encoding="utf-8")

        if metadata.had_existing_config:
            self.config_path.write_text(backup_content, encoding="utf-8")
        elif self.config_path.exists():
            self.config_path.unlink()

        if self.backup_path.exists():
            self.backup_path.unlink()
        self.rollback_metadata_path.unlink()

        return ContinueMountApplyResult(
            ok=True,
            summary="Continue mount was rolled back successfully.",
            detail=f"Config restored at: {self.config_path}",
        )

    def _ensure_parent_dirs(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_path.parent.mkdir(parents=True, exist_ok=True)
        self.rollback_metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def _updated_config_content(self, content: str, *, model_id: str, model_name: str) -> str:
        cleaned = self._strip_managed_block(content).rstrip()
        managed_block = self._managed_block(model_id=model_id, model_name=model_name)

        if not cleaned:
            return (
                "name: Modulo Managed Continue Config\n"
                "version: 1.0.0\n"
                "schema: v1\n"
                "models:\n"
                f"{managed_block}"
            )

        if "models:" not in cleaned:
            cleaned = f"{cleaned}\nmodels:"

        return f"{cleaned}\n{managed_block}"

    def _managed_block(self, *, model_id: str, model_name: str) -> str:
        return (
            f"{MANAGED_BLOCK_START}\n"
            f"  - name: {model_name}\n"
            "    provider: openai\n"
            f"    model: {model_id}\n"
            f"    apiBase: {self.api_base}\n"
            "    roles:\n"
            "      - chat\n"
            "      - edit\n"
            "      - apply\n"
            f"{MANAGED_BLOCK_END}\n"
        )

    @staticmethod
    def _strip_managed_block(content: str) -> str:
        pattern = (
            rf"\n?{re.escape(MANAGED_BLOCK_START)}.*?{re.escape(MANAGED_BLOCK_END)}\n?"
        )
        return re.sub(pattern, "\n", content, flags=re.DOTALL).rstrip("\n")
