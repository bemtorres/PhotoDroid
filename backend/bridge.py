import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self._progress = 0

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
        self.stateChanged.emit("detecting")
        self.log.emit("[backend] Fase 2 pendiente: adb_manager + device_manager")
        self.progress.emit(100)
        self.stateChanged.emit("idle")
        return json.dumps({"connected": False, "reason": "not_implemented"})

    @Slot(result=str)
    def startScan(self) -> str:
        self.stateChanged.emit("scanning")
        self.log.emit("[backend] Fase 3 pendiente: app/permission/process scanners")
        self.progress.emit(100)
        self.stateChanged.emit("idle")
        return json.dumps({"status": "not_implemented"})

    @Slot(int)
    def reportProgress(self, value: int) -> None:
        self._progress = max(0, min(100, value))
        self.progress.emit(self._progress)
