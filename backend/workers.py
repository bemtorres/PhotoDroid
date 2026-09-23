from pathlib import Path

from PySide6.QtCore import QThread, Signal

from backend.adb_manager import AdbError, AdbManager
from backend.app_scanner import AppScanner
from backend.device_manager import DeviceManager
from backend.permission_scanner import PermissionScanner
from backend.process_scanner import ProcessScanner
from backend.quarantine import QuarantineError, QuarantineManager
from backend.reports import ReportBuilder, ReportError
from backend.threat_engine import ThreatEngine

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_DIR = BASE_DIR / "rules"


class DetectDeviceWorker(QThread):
    succeeded = Signal(dict)
    failed = Signal(str)
    log = Signal(str)

    def __init__(self, adb_path: str = "adb", parent=None):
        super().__init__(parent)
        self.adb_path = adb_path

    def run(self) -> None:
        try:
            adb = AdbManager(self.adb_path)
            manager = DeviceManager(adb)
            exe = adb.resolve()
            self.log.emit(f"[adb] binario: {exe}")

            adb_version = adb.version()
            self.log.emit(f"[adb] {adb_version}")

            entries = manager.list_entries()
            online = [e for e in entries if e.online]
            detail = ", ".join(f"{e.serial}={e.state}" for e in entries) or "(vacía)"
            self.log.emit(f"[adb] devices: {detail}")
            self.log.emit(f"[adb] online: {len(online)}")

            info = manager.get_active(entries=entries)
            if info is None:
                reason = manager.describe_failure(entries)
                self.failed.emit(reason)
                return

            payload = info.to_dict()
            payload["adb_version"] = adb_version
            payload["device_count"] = len(entries)
            self.succeeded.emit(payload)
        except AdbError as exc:
            self.log.emit(f"[adb] error: {exc}")
            msg = str(exc)
            if "not found" in msg.lower():
                self.failed.emit("adb_not_found")
            else:
                self.failed.emit(msg)
        except Exception as exc:  # noqa: BLE001
            self.log.emit(f"[adb] unexpected: {exc}")
            self.failed.emit(f"unexpected: {exc}")


class AppListWorker(QThread):
    succeeded = Signal(list)
    failed = Signal(str)
    log = Signal(str)

    def __init__(self, adb_path: str, serial: str | None, include_system: bool, parent=None):
        super().__init__(parent)
        self.adb_path = adb_path
        self.serial = serial
        self.include_system = include_system

    def run(self) -> None:
        try:
            adb = AdbManager(self.adb_path)
            scanner = AppScanner(adb)
            self.log.emit("[apps] listando paquetes…")
            apps = scanner.list_apps(
                serial=self.serial,
                include_system=self.include_system,
                include_user=True,
            )
            self.succeeded.emit([a.to_dict() for a in apps])
        except AdbError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"unexpected: {exc}")


class PermissionScanWorker(QThread):
    succeeded = Signal(list, dict)
    failed = Signal(str)
    log = Signal(str)
    progress = Signal(int)
    threatsReady = Signal(dict)

    def __init__(
        self,
        adb_path: str,
        serial: str | None,
        packages: list[str],
        thresholds: dict | None = None,
        apps: list[dict] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.adb_path = adb_path
        self.serial = serial
        self.packages = packages
        self.thresholds = thresholds or {}
        self.apps = apps or []

    def run(self) -> None:
        try:
            adb = AdbManager(self.adb_path)
            scanner = PermissionScanner(adb)
            total = max(len(self.packages), 1)
            self.log.emit(f"[perms] analizando {len(self.packages)} paquetes…")

            results = []
            for index, package in enumerate(self.packages, start=1):
                results.append(scanner._scan_package(package, self.serial))
                if index % 5 == 0 or index == total:
                    self.progress.emit(int(index / total * 100))

            services = scanner.system_services(self.serial).to_dict()
            perm_dicts = [r.to_dict() for r in results]
            self.log.emit(
                f"[perms] listos: {len(results)} · overlay={len(services.get('overlay_apps', []))} · "
                f"a11y={len(services.get('accessibility_services', []))}"
            )

            engine = ThreatEngine(RULES_DIR, thresholds=self.thresholds)
            report = engine.evaluate(
                apps=self.apps,
                permissions=perm_dicts,
                services=services,
            )
            self.threatsReady.emit(report)
            self.log.emit(
                f"[threat] riesgo={report.get('risk_score')} ({report.get('risk_level')}) · "
                f"hallazgos={report.get('threat_count')}"
            )
            self.succeeded.emit(perm_dicts, services)
        except AdbError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"unexpected: {exc}")


class ProcessListWorker(QThread):
    succeeded = Signal(list)
    failed = Signal(str)
    log = Signal(str)

    def __init__(self, adb_path: str, serial: str | None, parent=None):
        super().__init__(parent)
        self.adb_path = adb_path
        self.serial = serial

    def run(self) -> None:
        try:
            adb = AdbManager(self.adb_path)
            scanner = ProcessScanner(adb)
            self.log.emit("[proc] leyendo procesos…")
            processes = scanner.list_processes(serial=self.serial)
            self.succeeded.emit([p.to_dict() for p in processes])
        except AdbError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"unexpected: {exc}")


class FullScanWorker(QThread):
    stage = Signal(str)
    progress = Signal(int)
    appsReady = Signal(list)
    permissionsReady = Signal(list, dict)
    processesReady = Signal(list)
    threatsReady = Signal(dict)
    succeeded = Signal(dict)
    failed = Signal(str)
    log = Signal(str)

    def __init__(
        self,
        adb_path: str,
        serial: str | None,
        include_system_apps: bool = True,
        permission_scan_system: bool = False,
        thresholds: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.adb_path = adb_path
        self.serial = serial
        self.include_system_apps = include_system_apps
        self.permission_scan_system = permission_scan_system
        self.thresholds = thresholds or {}
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _emit_progress(self, value: int) -> None:
        if not self._cancelled:
            self.progress.emit(value)

    def run(self) -> None:
        try:
            adb = AdbManager(self.adb_path)
            app_scanner = AppScanner(adb)
            perm_scanner = PermissionScanner(adb)
            proc_scanner = ProcessScanner(adb)

            self.stage.emit("apps")
            self.log.emit("[scan] 1/4 aplicaciones instaladas")
            self._emit_progress(5)
            apps = app_scanner.list_apps(
                serial=self.serial,
                include_system=self.include_system_apps,
                include_user=True,
            )
            app_dicts = [a.to_dict() for a in apps]
            self.appsReady.emit(app_dicts)
            self._emit_progress(30)
            if self._cancelled:
                return

            packages = [a.package for a in apps if self.permission_scan_system or not a.system]
            self.stage.emit("permissions")
            self.log.emit(f"[scan] 2/4 permisos de {len(packages)} paquetes")
            perm_results = []
            for index, package in enumerate(packages, start=1):
                if self._cancelled:
                    return
                perm_results.append(perm_scanner._scan_package(package, self.serial))
                if index % 5 == 0 or index == len(packages):
                    self._emit_progress(30 + int(index / max(len(packages), 1) * 45))

            services = perm_scanner.system_services(self.serial).to_dict()
            perm_dicts = [r.to_dict() for r in perm_results]
            self.permissionsReady.emit(perm_dicts, services)
            self._emit_progress(78)
            if self._cancelled:
                return

            self.stage.emit("threats")
            self.log.emit("[scan] 3/4 motor de amenazas")
            engine = ThreatEngine(RULES_DIR, thresholds=self.thresholds)
            report = engine.evaluate(apps=app_dicts, permissions=perm_dicts, services=services)
            self.threatsReady.emit(report)
            self._emit_progress(88)
            if self._cancelled:
                return

            self.stage.emit("processes")
            self.log.emit("[scan] 4/4 procesos activos")
            processes = proc_scanner.list_processes(serial=self.serial)
            self.processesReady.emit([p.to_dict() for p in processes])
            self._emit_progress(100)

            dangerous_count = sum(1 for r in perm_results if r.dangerous)
            self.succeeded.emit(
                {
                    "apps": len(apps),
                    "packages_scanned": len(packages),
                    "apps_with_dangerous": dangerous_count,
                    "processes": len(processes),
                    "services": services,
                    "risk_score": report.get("risk_score", 0),
                    "risk_level": report.get("risk_level", "unknown"),
                    "threat_count": report.get("threat_count", 0),
                }
            )
        except AdbError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"unexpected: {exc}")


class QuarantineWorker(QThread):
    succeeded = Signal(dict)
    failed = Signal(str)
    log = Signal(str)

    def __init__(
        self,
        adb_path: str,
        serial: str | None,
        action: str,
        package: str,
        system: bool | None = None,
        apps: list[dict] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.adb_path = adb_path
        self.serial = serial
        self.action = action
        self.package = package
        self.system = system
        self.apps = apps or []

    def run(self) -> None:
        try:
            adb = AdbManager(self.adb_path)
            manager = QuarantineManager(adb)
            self.log.emit(f"[quarantine] {self.action} → {self.package}")
            entry = manager.apply(
                self.action,
                self.package,
                serial=self.serial,
                system=self.system,
                confirmed=True,
                apps=self.apps,
            )
            self.log.emit(f"[quarantine] OK · {entry.action} · {entry.package}")
            self.succeeded.emit(entry.to_dict())
        except QuarantineError as exc:
            self.log.emit(f"[quarantine] error: {exc}")
            self.failed.emit(str(exc))
        except AdbError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"unexpected: {exc}")


class ExportReportWorker(QThread):
    succeeded = Signal(dict)
    failed = Signal(str)
    log = Signal(str)

    def __init__(self, fmt: str, payload: dict, output_dir: str = "reports", parent=None):
        super().__init__(parent)
        self.fmt = fmt
        self.payload = payload
        self.output_dir = output_dir

    def run(self) -> None:
        try:
            self.log.emit(f"[report] exportando {self.fmt}…")
            builder = ReportBuilder(self.output_dir)
            path = builder.export(self.payload, self.fmt)
            self.log.emit(f"[report] listo → {path}")
            self.succeeded.emit(
                {
                    "ok": True,
                    "format": self.fmt,
                    "path": str(path),
                    "filename": path.name,
                }
            )
        except ReportError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"unexpected: {exc}")
