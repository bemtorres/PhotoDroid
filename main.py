import sys
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow

from backend.bridge import Bridge

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "frontend" / "index.html"
APP_ICON_PATH = BASE_DIR / "assets" / "PhotoDroid.ico"
APP_ICON_FALLBACK = BASE_DIR / "assets" / "PhotoDroid_300.png"


def resolve_app_icon() -> Path | None:
    for path in (APP_ICON_PATH, APP_ICON_FALLBACK):
        if path.is_file():
            return path
    return None


class MainWindow(QMainWindow):
    def __init__(self, bridge: Bridge):
        super().__init__()
        self.setWindowTitle("PhotoDroid — Android Security Dashboard")
        self.resize(1280, 800)
        self.setMinimumSize(960, 640)

        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        self.channel = QWebChannel(self.view.page())
        self.bridge = bridge
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        self.view.loadFinished.connect(self._on_load_finished)
        self.view.load(QUrl.fromLocalFile(str(INDEX_PATH.resolve())))

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            self.bridge.log.emit("[ui] Error al cargar frontend/index.html")


def main() -> int:
    if hasattr(Qt, "AA_ShareOpenGLContexts"):
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)
    app.setApplicationName("PhotoDroid")
    app.setOrganizationName("PhotoDroid")
    icon_path = resolve_app_icon()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))

    bridge = Bridge()
    window = MainWindow(bridge)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
