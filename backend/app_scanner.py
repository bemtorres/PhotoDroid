from dataclasses import asdict, dataclass

from backend.adb_manager import AdbManager


@dataclass
class InstalledApp:
    package: str
    apk_path: str = ""
    system: bool = False
    version_name: str = ""
    version_code: str = ""
    installer: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class AppScanner:
    def __init__(self, adb: AdbManager):
        self.adb = adb

    def list_apps(
        self,
        serial: str | None = None,
        include_system: bool = True,
        include_user: bool = True,
        with_versions: bool = False,
    ) -> list[InstalledApp]:
        apps: dict[str, InstalledApp] = {}

        if include_user:
            for app in self._list_packages(serial, flag="-3"):
                apps[app.package] = app
        if include_system:
            for app in self._list_packages(serial, flag="-0"):
                apps.setdefault(app.package, app)

        if with_versions:
            for app in apps.values():
                self._fill_version(app, serial)

        return sorted(apps.values(), key=lambda a: (a.system, a.package.lower()))

    def _list_packages(self, serial: str | None, flag: str) -> list[InstalledApp]:
        result = self.adb.shell(f"pm list packages -f {flag}", serial=serial, timeout=20.0)
        if not result.ok:
            return []

        apps: list[InstalledApp] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line.startswith("package:"):
                continue
            payload = line[len("package:") :]
            if "=" in payload:
                path, _, package = payload.rpartition("=")
            else:
                path, package = "", payload
            package = package.strip()
            if not package:
                continue
            apps.append(
                InstalledApp(
                    package=package,
                    apk_path=path.strip(),
                    system=flag == "-0",
                )
            )
        return apps

    def _fill_version(self, app: InstalledApp, serial: str | None = None) -> None:
        result = self.adb.shell(
            f"dumpsys package {app.package}",
            serial=serial,
            timeout=12.0,
        )
        if not result.ok:
            return
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("versionName=") and not app.version_name:
                app.version_name = line.split("=", 1)[1].strip()
            elif line.startswith("versionCode=") and not app.version_code:
                app.version_code = line.split("=", 1)[1].strip().split()[0]
            elif line.startswith("installerPackageName=") and not app.installer:
                app.installer = line.split("=", 1)[1].strip() or "sideloaded"
            elif app.version_name and app.version_code and app.installer:
                break
