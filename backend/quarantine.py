from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.adb_manager import AdbManager, AdbResult

ALLOWED_ACTIONS = {"disable", "enable", "force_stop", "uninstall"}
SYSTEM_PREFIXES = (
    "com.android.",
    "android",
    "com.google.android.",
    "com.qualcomm.",
    "com.qti.",
    "com.mediatek.",
)


class QuarantineError(Exception):
    pass


@dataclass
class QuarantineEntry:
    timestamp: str
    action: str
    package: str
    serial: str | None
    ok: bool
    output: str = ""
    system: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class QuarantineManager:
    """Controlled mitigation with audit log. UI must confirm before apply()."""

    def __init__(
        self,
        adb: AdbManager | None = None,
        audit_path: str | Path | None = None,
    ):
        self.adb = adb or AdbManager()
        base = Path(audit_path) if audit_path else Path(__file__).resolve().parent.parent / "config"
        if base.suffix == ".jsonl" or str(base).endswith(".jsonl"):
            self.audit_path = base
        else:
            self.audit_path = base / "quarantine_audit.jsonl"

    @staticmethod
    def looks_system(package: str, apps: list[dict] | None = None) -> bool:
        if apps:
            for app in apps:
                if app.get("package") == package:
                    return bool(app.get("system"))
        return package.startswith(SYSTEM_PREFIXES)

    def apply(
        self,
        action: str,
        package: str,
        serial: str | None = None,
        system: bool | None = None,
        confirmed: bool = False,
        apps: list[dict] | None = None,
    ) -> QuarantineEntry:
        if not confirmed:
            raise QuarantineError("confirmation_required")
        if action not in ALLOWED_ACTIONS:
            raise QuarantineError(f"invalid_action:{action}")
        if not package or package.strip() in {".", ".."}:
            raise QuarantineError("invalid_package")

        is_system = self.looks_system(package, apps) if system is None else bool(system)
        if action == "uninstall" and is_system:
            raise QuarantineError("system_app_blocked")

        command = self._command(action, package)
        result = self.adb.shell(command, serial=serial, timeout=30.0)
        ok = self._is_success(action, package, result)

        entry = QuarantineEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            package=package,
            serial=serial,
            ok=ok,
            output=(result.stdout or result.stderr or "")[:500],
            system=is_system,
        )
        self.audit(entry)
        if not ok:
            raise QuarantineError(entry.output or f"adb_failed:{command}")
        return entry

    @staticmethod
    def _command(action: str, package: str) -> str:
        if action == "disable":
            return f"pm disable-user --user 0 {package}"
        if action == "enable":
            return f"pm enable {package}"
        if action == "force_stop":
            return f"am force-stop {package}"
        if action == "uninstall":
            return f"pm uninstall {package}"
        raise QuarantineError(f"invalid_action:{action}")

    @staticmethod
    def _is_success(action: str, package: str, result: AdbResult) -> bool:
        text = f"{result.stdout}\n{result.stderr}".lower()
        if action == "force_stop":
            return result.ok
        if action == "uninstall":
            return result.ok and "success" in text
        if action in {"disable", "enable"}:
            if not result.ok:
                return False
            if "disabled" in text or "enabled" in text or "success" in text:
                return True
            if "new state:" in text:
                return True
            return bool(result.stdout.strip()) and "exception" not in text
        return result.ok

    def audit(self, entry: QuarantineEntry) -> None:
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except OSError:
            pass

    def list_audit(self, limit: int = 50) -> list[dict]:
        if not self.audit_path.is_file():
            return []
        rows: list[dict] = []
        try:
            with open(self.audit_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []
        return rows[-limit:][::-1]
