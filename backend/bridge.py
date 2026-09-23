import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from backend.workers import (
    AppListWorker,
    DetectDeviceWorker,
    FullScanWorker,
    PermissionScanWorker,
    ProcessListWorker,
)

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "config" / "settings.json"


def load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"language": "en", "theme": "dark"}


class Bridge(QObject):
    log = Signal(str)
    progress = Signal(int)
    stateChanged = Signal(str)
    languageChanged = Signal(str)
    deviceFound = Signal("QVariant")
    deviceError = Signal(str)
    appsReady = Signal("QVariant")
    permissionsReady = Signal("QVariant")
    servicesReady = Signal("QVariant")
    processesReady = Signal("QVariant")
    scanFinished = Signal("QVariant")
    scanError = Signal(str)
    scanStage = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self._progress = 0
        self.current_serial: str | None = None
        self._last_packages: list[str] = []
        self._detect_worker: DetectDeviceWorker | None = None
        self._apps_worker: AppListWorker | None = None
        self._perms_worker: PermissionScanWorker | None = None
        self._procs_worker: ProcessListWorker | None = None
        self._scan_worker: FullScanWorker | None = None

    def _adb_path(self) -> str:
        return self.settings.get("adb_path", "adb")

    @Slot(result=str)
    def ping(self) -> str:
        return "pong"

    @Slot(result=str)
    def getSettings(self) -> str:
        return json.dumps(self.settings, ensure_ascii=False)

    @Slot(result=str)
    def getAppInfo(self) -> str:
        return json.dumps(
            {
                "name": "PhotoDroid",
                "version": "0.1.0",
                "language": self.settings.get("language", "en"),
            },
            ensure_ascii=False,
        )

    @Slot(result=str)
    def detectDevice(self) -> str:
        if self._detect_worker and self._detect_worker.isRunning():
            return json.dumps({"started": False, "reason": "already_running"})

        self.stateChanged.emit("detecting")
        self.progress.emit(15)
        self.log.emit("[adb] buscando dispositivos…")

        self._detect_worker = DetectDeviceWorker(adb_path=self._adb_path())
        self._detect_worker.succeeded.connect(self._on_device_found)
        self._detect_worker.failed.connect(self._on_device_error)
        self._detect_worker.finished.connect(
            lambda: self._cleanup("_detect_worker")
        )
        self._detect_worker.start()
        return json.dumps({"started": True})

    def _on_device_found(self, info: dict) -> None:
        self.progress.emit(100)
        self.current_serial = info.get("serial")
        self.log.emit(
            f"[device] {info.get('model', '?')} · Android {info.get('android', '?')} · {info.get('serial', '?')}"
        )
        if info.get("battery") is not None:
            self.log.emit(f"[device] batería: {info['battery']}%")
        self.deviceFound.emit(info)

    def _on_device_error(self, reason: str) -> None:
        self.progress.emit(100)
        self.current_serial = None
        self.log.emit(f"[device] error: {reason}")
        self.deviceError.emit(reason)

    @Slot(result=str)
    def listApps(self) -> str:
        if self._worker_running("_apps_worker"):
            return json.dumps({"started": False, "reason": "already_running"})

        include_system = self.settings.get("scan", {}).get("include_system_apps", True)
        self.stateChanged.emit("loading_apps")
        self._apps_worker = AppListWorker(
            adb_path=self._adb_path(),
            serial=self.current_serial,
            include_system=include_system,
        )
        self._apps_worker.log.connect(self.log)
        self._apps_worker.succeeded.connect(self._on_apps)
        self._apps_worker.failed.connect(self._on_scan_error)
        self._apps_worker.finished.connect(lambda: self._cleanup("_apps_worker"))
        self._apps_worker.start()
        return json.dumps({"started": True})

    def _on_apps(self, apps: list) -> None:
        self.progress.emit(100)
        self.stateChanged.emit("idle")
        self._last_packages = [a.get("package", "") for a in apps if a.get("package")]
        self.log.emit(f"[apps] {len(apps)} aplicaciones")
        self.appsReady.emit(apps)

    @Slot(result=str)
    def scanPermissions(self) -> str:
        if self._worker_running("_perms_worker"):
            return json.dumps({"started": False, "reason": "already_running"})

        packages = list(self._last_packages)
        if not packages:
            self.log.emit("[perms] lista de paquetes vacía — ejecuta antes listApps")
            self.scanError.emit("no_packages")
            return json.dumps({"started": False, "reason": "no_packages"})

        scan_system = self.settings.get("scan", {}).get("permission_scan_system", False)
        if not scan_system:
            packages = [p for p in packages if not str(p).startswith(("com.android.", "android.", "com.google.android."))]

        self.stateChanged.emit("scanning_permissions")
        self.progress.emit(0)
        self._perms_worker = PermissionScanWorker(
            adb_path=self._adb_path(),
            serial=self.current_serial,
            packages=packages,
        )
        self._perms_worker.log.connect(self.log)
        self._perms_worker.progress.connect(self.progress)
        self._perms_worker.succeeded.connect(self._on_permissions)
        self._perms_worker.failed.connect(self._on_scan_error)
        self._perms_worker.finished.connect(lambda: self._cleanup("_perms_worker"))
        self._perms_worker.start()
        return json.dumps({"started": True, "packages": len(packages)})

    def _on_permissions(self, results: list, services: dict) -> None:
        self.progress.emit(100)
        self.stateChanged.emit("idle")
        self.log.emit(f"[perms] {len(results)} paquetes analizados")
        self.permissionsReady.emit(results)
        self.servicesReady.emit(services)

    @Slot(result=str)
    def listProcesses(self) -> str:
        if self._worker_running("_procs_worker"):
            return json.dumps({"started": False, "reason": "already_running"})

        self.stateChanged.emit("loading_processes")
        self._procs_worker = ProcessListWorker(
            adb_path=self._adb_path(),
            serial=self.current_serial,
        )
        self._procs_worker.log.connect(self.log)
        self._procs_worker.succeeded.connect(self._on_processes)
        self._procs_worker.failed.connect(self._on_scan_error)
        self._procs_worker.finished.connect(lambda: self._cleanup("_procs_worker"))
        self._procs_worker.start()
        return json.dumps({"started": True})

    def _on_processes(self, processes: list) -> None:
        self.progress.emit(100)
        self.stateChanged.emit("idle")
        self.log.emit(f"[proc] {len(processes)} procesos")
        self.processesReady.emit(processes)

    @Slot(result=str)
    def startScan(self) -> str:
        if self._worker_running("_scan_worker"):
            return json.dumps({"started": False, "reason": "already_running"})

        include_system = self.settings.get("scan", {}).get("include_system_apps", True)
        permission_scan_system = self.settings.get("scan", {}).get("permission_scan_system", False)

        self.stateChanged.emit("scanning")
        self.progress.emit(0)
        self.log.emit("[scan] escaneo completo iniciado")

        self._scan_worker = FullScanWorker(
            adb_path=self._adb_path(),
            serial=self.current_serial,
            include_system_apps=include_system,
            permission_scan_system=permission_scan_system,
        )
        self._scan_worker.log.connect(self.log)
        self._scan_worker.progress.connect(self.progress)
        self._scan_worker.stage.connect(self.scanStage)
        self._scan_worker.appsReady.connect(self._on_scan_apps)
        self._scan_worker.permissionsReady.connect(self._on_permissions)
        self._scan_worker.processesReady.connect(self._on_processes)
        self._scan_worker.succeeded.connect(self._on_scan_done)
        self._scan_worker.failed.connect(self._on_scan_error)
        self._scan_worker.finished.connect(lambda: self._cleanup("_scan_worker"))
        self._scan_worker.start()
        return json.dumps({"started": True})

    def _on_scan_apps(self, apps: list) -> None:
        self._last_packages = [a.get("package", "") for a in apps if a.get("package")]
        self.appsReady.emit(apps)

    def _on_scan_done(self, summary: dict) -> None:
        self.progress.emit(100)
        self.stateChanged.emit("idle")
        self.log.emit(
            f"[scan] OK · apps={summary.get('apps')} · "
            f"perms={summary.get('packages_scanned')} · "
            f"riesgo={summary.get('apps_with_dangerous')} · "
            f"procs={summary.get('processes')}"
        )
        self.scanFinished.emit(summary)

    def _on_scan_error(self, reason: str) -> None:
        self.progress.emit(100)
        self.stateChanged.emit("idle")
        self.log.emit(f"[scan] error: {reason}")
        self.scanError.emit(reason)

    def _worker_running(self, attr: str) -> bool:
        worker = getattr(self, attr, None)
        return bool(worker and worker.isRunning())

    def _cleanup(self, attr: str) -> None:
        worker = getattr(self, attr, None)
        if worker:
            worker.deleteLater()
            setattr(self, attr, None)

    @Slot(int)
    def reportProgress(self, value: int) -> None:
        self._progress = max(0, min(100, value))
        self.progress.emit(self._progress)
