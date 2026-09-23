from PySide6.QtCore import QThread, Signal

from backend.adb_manager import AdbError, AdbManager
from backend.app_scanner import AppScanner
from backend.device_manager import DeviceManager
from backend.permission_scanner import PermissionScanner
from backend.process_scanner import ProcessScanner


class DetectDeviceWorker(QThread):
    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, adb_path: str = "adb", parent=None):
        super().__init__(parent)
        self.adb_path = adb_path

    def run(self) -> None:
        try:
            adb = AdbManager(self.adb_path)
            manager = DeviceManager(adb)

            adb_version = adb.version()
            entries = manager.list_entries()
            info = manager.get_active()

            if info is None:
                reason = manager.describe_failure(entries)
                self.failed.emit(reason)
                return

            payload = info.to_dict()
            payload["adb_version"] = adb_version
            payload["device_count"] = len(entries)
            self.succeeded.emit(payload)
        except AdbError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
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

    def __init__(
        self,
        adb_path: str,
        serial: str | None,
        packages: list[str],
        parent=None,
    ):
        super().__init__(parent)
        self.adb_path = adb_path
        self.serial = serial
        self.packages = packages

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
            self.log.emit(
                f"[perms] listos: {len(results)} · overlay={len(services.get('overlay_apps', []))} · "
                f"a11y={len(services.get('accessibility_services', []))}"
            )
            self.succeeded.emit([r.to_dict() for r in results], services)
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
    succeeded = Signal(dict)
    failed = Signal(str)
    log = Signal(str)

    def __init__(
        self,
        adb_path: str,
        serial: str | None,
        include_system_apps: bool = True,
        permission_scan_system: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.adb_path = adb_path
        self.serial = serial
        self.include_system_apps = include_system_apps
        self.permission_scan_system = permission_scan_system
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
            self.log.emit("[scan] 1/3 aplicaciones instaladas")
            self._emit_progress(5)
            apps = app_scanner.list_apps(
                serial=self.serial,
                include_system=self.include_system_apps,
                include_user=True,
            )
            self.appsReady.emit([a.to_dict() for a in apps])
            self._emit_progress(35)
            if self._cancelled:
                return

            packages = [a.package for a in apps if self.permission_scan_system or not a.system]
            self.stage.emit("permissions")
            self.log.emit(f"[scan] 2/3 permisos de {len(packages)} paquetes")
            perm_results = []
            for index, package in enumerate(packages, start=1):
                if self._cancelled:
                    return
                perm_results.append(perm_scanner._scan_package(package, self.serial))
                if index % 5 == 0 or index == len(packages):
                    self._emit_progress(35 + int(index / max(len(packages), 1) * 45))

            services = perm_scanner.system_services(self.serial).to_dict()
            self.permissionsReady.emit([r.to_dict() for r in perm_results], services)
            self._emit_progress(85)
            if self._cancelled:
                return

            self.stage.emit("processes")
            self.log.emit("[scan] 3/3 procesos activos")
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
                }
            )
        except AdbError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"unexpected: {exc}")
