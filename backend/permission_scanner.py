from dataclasses import asdict, dataclass, field

from backend.adb_manager import AdbManager

DANGEROUS_PERMISSIONS = {
    "android.permission.SYSTEM_ALERT_WINDOW": "Overlay",
    "android.permission.BIND_ACCESSIBILITY_SERVICE": "Accessibility",
    "android.permission.REQUEST_INSTALL_PACKAGES": "Install apps",
    "android.permission.MANAGE_EXTERNAL_STORAGE": "All files access",
    "android.permission.READ_SMS": "Read SMS",
    "android.permission.RECEIVE_SMS": "Receive SMS",
    "android.permission.SEND_SMS": "Send SMS",
    "android.permission.READ_CONTACTS": "Read contacts",
    "android.permission.READ_CALL_LOG": "Call log",
    "android.permission.RECORD_AUDIO": "Microphone",
    "android.permission.CAMERA": "Camera",
    "android.permission.READ_PHONE_STATE": "Phone state",
    "android.permission.PROCESS_OUTGOING_CALLS": "Call interception",
    "android.permission.REQUEST_DELETE_PACKAGES": "Uninstall apps",
    "android.permission.QUERY_ALL_PACKAGES": "See all apps",
}


@dataclass
class AppPermissions:
    package: str
    permissions: list[str] = field(default_factory=list)
    dangerous: list[str] = field(default_factory=list)
    overlay: bool = False
    accessibility: bool = False

    @property
    def risk_score(self) -> int:
        score = len(self.dangerous) * 8
        if self.overlay:
            score += 20
        if self.accessibility:
            score += 25
        return min(score, 100)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["risk_score"] = self.risk_score
        data["labels"] = [DANGEROUS_PERMISSIONS[p] for p in self.dangerous if p in DANGEROUS_PERMISSIONS]
        return data


@dataclass
class SystemServices:
    overlay_apps: list[str] = field(default_factory=list)
    accessibility_services: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class PermissionScanner:
    def __init__(self, adb: AdbManager):
        self.adb = adb

    def scan_apps(
        self,
        packages: list[str],
        serial: str | None = None,
        limit: int = 0,
    ) -> list[AppPermissions]:
        targets = packages[:limit] if limit > 0 else packages
        return [self._scan_package(pkg, serial) for pkg in targets]

    def _scan_package(self, package: str, serial: str | None = None) -> AppPermissions:
        info = AppPermissions(package=package)
        result = self.adb.shell(f"dumpsys package {package}", serial=serial, timeout=12.0)
        if not result.ok:
            return info

        in_requested = False
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.lower().startswith("requested permissions:"):
                in_requested = True
                continue

            if in_requested:
                if line.endswith(":"):
                    in_requested = False
                    continue
                perm = line.rstrip(":")
                info.permissions.append(perm)
                if perm in DANGEROUS_PERMISSIONS:
                    info.dangerous.append(perm)
                if perm == "android.permission.SYSTEM_ALERT_WINDOW":
                    info.overlay = True

        info.accessibility = self._has_accessibility(package, serial)
        if info.accessibility:
            marker = "android.permission.BIND_ACCESSIBILITY_SERVICE"
            if marker not in info.permissions:
                info.permissions.append(marker)
            if marker not in info.dangerous:
                info.dangerous.append(marker)

        if not info.overlay:
            info.overlay = self._has_overlay_appop(package, serial)

        return info

    def _has_accessibility(self, package: str, serial: str | None) -> bool:
        result = self.adb.shell(
            "settings get secure enabled_accessibility_services",
            serial=serial,
            timeout=8.0,
        )
        if not result.ok:
            return False
        return package.lower() in result.stdout.lower()

    def _has_overlay_appop(self, package: str, serial: str | None) -> bool:
        result = self.adb.shell(
            f"appops get {package} SYSTEM_ALERT_WINDOW",
            serial=serial,
            timeout=8.0,
        )
        return result.ok and "allow" in result.stdout.lower()

    def system_services(self, serial: str | None = None) -> SystemServices:
        services = SystemServices()

        a11y = self.adb.shell(
            "settings get secure enabled_accessibility_services",
            serial=serial,
            timeout=8.0,
        )
        if a11y.ok:
            raw = a11y.stdout.strip()
            if raw and raw != "null":
                for part in raw.split(":"):
                    part = part.strip()
                    if "/" in part:
                        services.accessibility_services.append(part.split("/", 1)[0])
                    elif part:
                        services.accessibility_services.append(part)

        dump = self.adb.shell(
            "dumpsys appops",
            serial=serial,
            timeout=20.0,
        )
        if dump.ok:
            current_pkg = ""
            for line in dump.stdout.splitlines():
                line = line.strip()
                if line.startswith("Package ") and line.endswith(":"):
                    current_pkg = line[len("Package ") : -1].strip()
                    continue
                if (
                    current_pkg
                    and "SYSTEM_ALERT_WINDOW" in line
                    and "mode=allow" in line
                    and current_pkg not in services.overlay_apps
                ):
                    services.overlay_apps.append(current_pkg)

        return services
