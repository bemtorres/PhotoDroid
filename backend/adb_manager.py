import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


class AdbError(Exception):
    pass


@dataclass
class AdbResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    code: int = -1

    @property
    def output(self) -> str:
        return self.stdout or self.stderr


@dataclass
class AdbDeviceEntry:
    serial: str
    state: str
    model: str = ""
    product: str = ""
    device: str = ""
    transport_id: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def online(self) -> bool:
        return self.state == "device"


COMMON_ADB_PATHS = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb",
    Path(os.environ.get("ANDROID_HOME", "")) / "platform-tools" / "adb.exe",
    Path(os.environ.get("ANDROID_HOME", "")) / "platform-tools" / "adb",
    Path(os.environ.get("ANDROID_SDK_ROOT", "")) / "platform-tools" / "adb.exe",
    Path(os.environ.get("ANDROID_SDK_ROOT", "")) / "platform-tools" / "adb",
    Path.home() / "Library" / "Android" / "sdk" / "platform-tools" / "adb",
    Path("/usr/bin/adb"),
    Path("/usr/local/bin/adb"),
    Path.home() / "Android" / "Sdk" / "platform-tools" / "adb",
)


def _run_kwargs() -> dict:
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return kwargs


class AdbManager:
    def __init__(self, adb_path: str = "adb", timeout: float = 15.0):
        self.adb_path = adb_path or "adb"
        self.timeout = timeout
        self._resolved: str | None = None

    def resolve(self) -> str:
        if self._resolved:
            return self._resolved

        candidate = (self.adb_path or "").strip()
        if candidate and candidate.lower() not in {"adb", "adb.exe"}:
            p = Path(candidate).expanduser()
            if p.is_file():
                self._resolved = str(p)
                return self._resolved
            found = shutil.which(candidate)
            if found:
                self._resolved = found
                return self._resolved

        found = shutil.which("adb") or shutil.which("adb.exe")
        if found:
            self._resolved = found
            return self._resolved

        for path in COMMON_ADB_PATHS:
            try:
                if path and str(path) not in {".", ""} and path.is_file():
                    self._resolved = str(path)
                    return self._resolved
            except OSError:
                continue

        raise AdbError(
            "ADB not found. Install Android platform-tools or set adb_path in config/settings.json"
        )

    def run(self, *args: str, timeout: float | None = None) -> AdbResult:
        exe = self.resolve()
        cmd = [exe, *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout or self.timeout,
                **_run_kwargs(),
            )
        except FileNotFoundError as exc:
            self._resolved = None
            raise AdbError(f"ADB executable not found: {exe}") from exc
        except subprocess.TimeoutExpired:
            return AdbResult(
                ok=False,
                stderr=f"adb timed out after {timeout or self.timeout}s",
                code=124,
            )

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        return AdbResult(ok=proc.returncode == 0, stdout=stdout, stderr=stderr, code=proc.returncode)

    def version(self) -> str:
        result = self.run("version")
        if not result.ok:
            raise AdbError(result.stderr or "adb version failed")
        return result.stdout.splitlines()[0] if result.stdout else ""

    def start_server(self) -> None:
        self.run("start-server", timeout=20.0)

    def list_devices(self) -> list[AdbDeviceEntry]:
        result = self.run("devices", "-l")
        if not result.ok and not result.stdout:
            raise AdbError(result.stderr or "adb devices failed")
        entries = self._parse_devices(result.stdout)
        if not entries:
            self.run("start-server", timeout=20.0)
            result = self.run("devices", "-l")
            if not result.ok and not result.stdout:
                raise AdbError(result.stderr or "adb devices failed")
            entries = self._parse_devices(result.stdout)
        return entries

    def shell(self, command: str, serial: str | None = None, timeout: float | None = None) -> AdbResult:
        args: list[str] = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["shell", command])
        return self.run(*args, timeout=timeout)

    @staticmethod
    def _parse_devices(raw: str) -> list[AdbDeviceEntry]:
        entries: list[AdbDeviceEntry] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices"):
                continue
            if line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            if serial == "adb" and state == "devices":
                continue
            fields: dict[str, str] = {}
            for token in parts[2:]:
                if ":" in token:
                    key, _, value = token.partition(":")
                    fields[key] = value
            entries.append(
                AdbDeviceEntry(
                    serial=serial,
                    state=state,
                    model=fields.get("model", ""),
                    product=fields.get("product", ""),
                    device=fields.get("device", ""),
                    transport_id=fields.get("transport_id", ""),
                    extra=fields,
                )
            )
        return entries

    @staticmethod
    def first_online(entries: list[AdbDeviceEntry]) -> AdbDeviceEntry | None:
        for entry in entries:
            if entry.online:
                return entry
        return None
