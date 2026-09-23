from dataclasses import asdict, dataclass

from backend.adb_manager import AdbManager


@dataclass
class ProcessEntry:
    pid: str
    name: str
    user: str = ""
    ppid: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ProcessScanner:
    def __init__(self, adb: AdbManager):
        self.adb = adb

    def list_processes(self, serial: str | None = None) -> list[ProcessEntry]:
        raw = self._run_ps(serial)
        if not raw:
            raw = self._run_ps_alt(serial)
        return self._parse_ps(raw)

    def _run_ps(self, serial: str | None) -> str:
        result = self.adb.shell("ps -A -o PID,PPID,USER,NAME", serial=serial, timeout=20.0)
        if result.ok and result.stdout:
            return result.stdout
        return ""

    def _run_ps_alt(self, serial: str | None) -> str:
        result = self.adb.shell("ps -A", serial=serial, timeout=20.0)
        return result.stdout if result.ok else ""

    @staticmethod
    def _parse_ps(raw: str) -> list[ProcessEntry]:
        entries: list[ProcessEntry] = []
        if not raw:
            return entries

        lines = raw.splitlines()
        header = lines[0].lower() if lines else ""
        start = 1 if "pid" in header else 0
        header_tokens = header.split()
        has_ppid = "ppid" in header_tokens
        has_user = "user" in header_tokens

        for line in lines[start:]:
            parts = line.split()
            if not parts:
                continue

            if has_user and has_ppid and len(parts) >= 4:
                entries.append(
                    ProcessEntry(pid=parts[0], ppid=parts[1], user=parts[2], name=" ".join(parts[3:]))
                )
            elif len(parts) >= 2 and parts[0].isdigit():
                user = ""
                name_parts = parts[1:]
                if name_parts and not name_parts[0].isdigit() and has_user:
                    user = name_parts[0]
                    name_parts = name_parts[1:]
                entries.append(
                    ProcessEntry(pid=parts[0], user=user, name=" ".join(name_parts) or parts[-1])
                )
            elif len(parts) >= 2 and not parts[0].isdigit():
                entries.append(ProcessEntry(pid="?", name=line.strip()))

        return entries
