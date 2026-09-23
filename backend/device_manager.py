from dataclasses import asdict, dataclass

from backend.adb_manager import AdbDeviceEntry, AdbError, AdbManager


@dataclass
class DeviceInfo:
    serial: str
    state: str
    model: str = ""
    brand: str = ""
    device: str = ""
    product: str = ""
    android: str = ""
    sdk: str = ""
    release_type: str = ""
    battery: int | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["connected"] = self.state == "device"
        return data


GETPROP_KEYS = {
    "model": "ro.product.model",
    "brand": "ro.product.brand",
    "device": "ro.product.device",
    "product": "ro.product.name",
    "android": "ro.build.version.release",
    "sdk": "ro.build.version.sdk",
    "release_type": "ro.build.type",
}


class DeviceManager:
    def __init__(self, adb: AdbManager | None = None):
        self.adb = adb or AdbManager()

    def list_entries(self) -> list[AdbDeviceEntry]:
        self.adb.start_server()
        return self.adb.list_devices()

    def get_active(self) -> DeviceInfo | None:
        entries = self.list_entries()
        entry = self.adb.first_online(entries)
        if not entry:
            return None
        return self.get_info(entry)

    def get_info(self, entry: AdbDeviceEntry) -> DeviceInfo:
        info = DeviceInfo(
            serial=entry.serial,
            state=entry.state,
            model=entry.model,
            product=entry.product,
            device=entry.device,
        )

        for attr, key in GETPROP_KEYS.items():
            value = self.getprop(key, entry.serial)
            if value:
                setattr(info, attr, value)

        if not info.model:
            info.model = entry.serial

        info.battery = self.battery_level(entry.serial)
        return info

    def getprop(self, prop: str, serial: str | None = None) -> str:
        result = self.adb.shell(f"getprop {prop}", serial=serial, timeout=8.0)
        if not result.ok:
            return ""
        return result.stdout.strip()

    def battery_level(self, serial: str | None = None) -> int | None:
        result = self.adb.shell("dumpsys battery", serial=serial, timeout=8.0)
        if not result.ok:
            return None
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                try:
                    return int(line.split(":", 1)[1].strip())
                except ValueError:
                    return None
        return None

    def describe_failure(self, entries: list[AdbDeviceEntry]) -> str:
        if not entries:
            return "no_devices"
        states = {e.state for e in entries}
        if states <= {"unauthorized"}:
            return "unauthorized"
        if states <= {"offline"}:
            return "offline"
        if "no permissions" in " ".join(states):
            return "no_permissions"
        return "no_online_device"
