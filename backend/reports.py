from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FORMATS = ("json", "csv", "html", "pdf")


class ReportError(Exception):
    pass


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_serial(serial: str | None) -> str:
    return (serial or "unknown").replace(":", "_").replace("/", "_") or "unknown"


class ReportBuilder:
    def __init__(self, output_dir: str | Path = "reports"):
        base = Path(output_dir)
        if not base.is_absolute():
            base = Path(__file__).resolve().parent.parent / base
        self.output_dir = base

    def build_payload(
        self,
        *,
        device: dict | None = None,
        apps: list[dict] | None = None,
        permissions: list[dict] | None = None,
        processes: list[dict] | None = None,
        threats: dict | None = None,
        services: dict | None = None,
        summary: dict | None = None,
        language: str = "en",
    ) -> dict[str, Any]:
        threats = threats or {}
        return {
            "app": "PhotoDroid",
            "version": "0.2.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "language": language,
            "device": device or {},
            "summary": summary or {},
            "threats": {
                "risk_score": threats.get("risk_score", 0),
                "risk_level": threats.get("risk_level", "unknown"),
                "threat_count": threats.get("threat_count", 0),
                "findings": threats.get("findings", []),
                "services": services or threats.get("services", {}),
            },
            "apps": apps or [],
            "permissions": permissions or [],
            "processes": processes or [],
        }

    def export(self, payload: dict, fmt: str = "html") -> Path:
        fmt = (fmt or "html").lower()
        if fmt not in FORMATS:
            raise ReportError(f"unsupported_format:{fmt}")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"informe_{_safe_serial(payload.get('device', {}).get('serial'))}_{_timestamp()}"
        if fmt == "json":
            path = self.output_dir / f"{stem}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return path
        if fmt == "csv":
            path = self.output_dir / f"{stem}.csv"
            self._write_csv(path, payload)
            return path
        if fmt == "html":
            path = self.output_dir / f"{stem}.html"
            path.write_text(self.render_html(payload), encoding="utf-8")
            return path
        path = self.output_dir / f"{stem}.pdf"
        self._write_pdf(path, payload)
        return path

    @staticmethod
    def _write_csv(path: Path, payload: dict) -> None:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["section", "key", "value"])
            device = payload.get("device") or {}
            for key in ("serial", "model", "brand", "android", "sdk", "battery"):
                writer.writerow(["device", key, device.get(key, "")])
            threats = payload.get("threats") or {}
            writer.writerow(["threats", "risk_score", threats.get("risk_score", 0)])
            writer.writerow(["threats", "risk_level", threats.get("risk_level", "")])
            writer.writerow(["threats", "threat_count", threats.get("threat_count", 0)])
            for finding in threats.get("findings") or []:
                reasons = "; ".join(
                    f"{r.get('code')}:{r.get('detail')}(+{r.get('weight')})"
                    for r in finding.get("reasons") or []
                )
                writer.writerow(
                    [
                        "finding",
                        finding.get("package", ""),
                        f"score={finding.get('score')}; level={finding.get('level')}; {reasons}",
                    ]
                )
            for app in payload.get("apps") or []:
                writer.writerow(
                    [
                        "app",
                        app.get("package", ""),
                        f"system={app.get('system')}; apk={app.get('apk_path', '')}",
                    ]
                )

    @staticmethod
    def render_html(payload: dict) -> str:
        device = payload.get("device") or {}
        threats = payload.get("threats") or {}
        findings = threats.get("findings") or []
        apps = payload.get("apps") or []
        e = html.escape

        finding_rows = "".join(
            "<tr>"
            f"<td>{e(str(f.get('package', '')))}</td>"
            f"<td>{e(str(f.get('score', 0)))}</td>"
            f"<td>{e(str(f.get('level', '')))}</td>"
            f"<td>{e('; '.join(str(r.get('detail', r.get('code', ''))) for r in f.get('reasons') or []))}</td>"
            "</tr>"
            for f in findings
        ) or '<tr><td colspan="4">—</td></tr>'

        app_rows = "".join(
            "<tr>"
            f"<td>{e(str(a.get('package', '')))}</td>"
            f"<td>{'system' if a.get('system') else 'user'}</td>"
            f"<td>{e(str(a.get('apk_path', '')))}</td>"
            "</tr>"
            for a in apps[:200]
        ) or '<tr><td colspan="3">—</td></tr>'

        risk = threats.get("risk_level", "unknown")
        return f"""<!DOCTYPE html>
<html lang="{e(str(payload.get('language', 'en')))}">
<head>
  <meta charset="utf-8" />
  <title>PhotoDroid — {e(str(device.get('serial', 'report')))}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #111; }}
    h1 {{ font-size: 1.4rem; }} h2 {{ font-size: 1.1rem; margin-top: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
    .meta {{ color: #555; font-size: 13px; }}
    .risk {{ font-weight: 700; color: #b91c1c; }}
  </style>
</head>
<body>
  <h1>PhotoDroid Security Report</h1>
  <p class="meta">{e(str(payload.get('generated_at', '')))} · {e(str(payload.get('version', '')))}</p>
  <p class="meta">Device: {e(str(device.get('model', '?')))} · Android {e(str(device.get('android', '?')))} · {e(str(device.get('serial', '?')))}</p>
  <p>Risk: <span class="risk">{e(str(risk))} {threats.get('risk_score', 0)}/100</span> · Findings: {threats.get('threat_count', 0)}</p>
  <h2>Findings</h2>
  <table><thead><tr><th>Package</th><th>Score</th><th>Level</th><th>Reasons</th></tr></thead>
  <tbody>{finding_rows}</tbody></table>
  <h2>Apps ({len(apps)})</h2>
  <table><thead><tr><th>Package</th><th>Type</th><th>APK</th></tr></thead>
  <tbody>{app_rows}</tbody></table>
</body>
</html>"""

    @staticmethod
    def _pdf_escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _write_pdf(self, path: Path, payload: dict) -> None:
        """Minimal single/multi-page text PDF (no external deps)."""
        device = payload.get("device") or {}
        threats = payload.get("threats") or {}
        lines = [
            "PhotoDroid Security Report",
            f"Generated: {payload.get('generated_at', '')}",
            f"Device: {device.get('model', '?')} / Android {device.get('android', '?')} / {device.get('serial', '?')}",
            f"Risk: {threats.get('risk_level', '?')} {threats.get('risk_score', 0)}/100",
            f"Findings: {threats.get('threat_count', 0)}  Apps: {len(payload.get('apps') or [])}",
            "",
            "Top findings:",
        ]
        for f in (threats.get("findings") or [])[:40]:
            reasons = ", ".join(str(r.get("detail", r.get("code", ""))) for r in f.get("reasons") or [])
            lines.append(f"- {f.get('package')} score={f.get('score')} [{f.get('level')}] {reasons}")

        # Paginate ~50 lines/page
        pages = [lines[i : i + 50] for i in range(0, max(len(lines), 1), 50)] or [[]]
        objects: list[bytes] = []

        def add(obj: str | bytes) -> int:
            objects.append(obj.encode("latin-1", errors="replace") if isinstance(obj, str) else obj)
            return len(objects)

        font_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        page_ids: list[int] = []
        content_ids: list[int] = []

        for page_lines in pages:
            y_start = 800
            content_parts = ["BT /F1 10 Tf 40 820 Td 14 TL"]
            for i, line in enumerate(page_lines):
                safe = self._pdf_escape(line[:110])
                if i == 0:
                    content_parts.append(f"({safe}) Tj")
                else:
                    content_parts.append(f"T* ({safe}) Tj")
            content_parts.append("ET")
            stream = "\n".join(content_parts)
            content_id = add(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
            content_ids.append(content_id)

        pages_id_placeholder = len(objects) + len(pages) + 1
        for content_id in content_ids:
            page_id = add(
                f"<< /Type /Page /Parent {pages_id_placeholder} 0 R "
                f"/MediaBox [0 0 612 792] /Contents {content_id} 0 R "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>"
            )
            page_ids.append(page_id)

        kids = " ".join(f"{pid} 0 R" for pid in page_ids)
        pages_id = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
        assert pages_id == pages_id_placeholder or True
        catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

        # If placeholder mismatch, rebuild is complex — use actual pages_id
        # Rebuild page objects if pages_id != placeholder (unlikely but safe)
        if pages_id != pages_id_placeholder:
            # Patch: we cannot easily patch; regenerate with correct parent id
            return self._write_pdf_v2(path, payload)

        out = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n".encode("ascii"))
            out.extend(obj if isinstance(obj, bytes) else obj.encode("latin-1", errors="replace"))
            out.extend(b"\nendobj\n")
        xref_pos = len(out)
        out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        out.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
        )
        path.write_bytes(bytes(out))

    def _write_pdf_v2(self, path: Path, payload: dict) -> None:
        device = payload.get("device") or {}
        threats = payload.get("threats") or {}
        lines = [
            "PhotoDroid Security Report",
            f"Generated: {payload.get('generated_at', '')}",
            f"Device: {device.get('model', '?')} Android {device.get('android', '?')} {device.get('serial', '?')}",
            f"Risk: {threats.get('risk_level', '?')} {threats.get('risk_score', 0)}/100",
            "",
            "Findings:",
        ]
        for f in (threats.get("findings") or [])[:30]:
            lines.append(f"- {f.get('package')} ({f.get('score')}) {f.get('level')}")
        pages = [lines[i : i + 45] for i in range(0, max(len(lines), 1), 45)] or [[]]

        # Build object list with known structure:
        # 1: catalog, 2: pages, 3: font, then content+page pairs
        n_pages = len(pages)
        font_obj = 3
        first_content = 4
        # content ids: 4,6,8,... page ids: 5,7,9,...
        page_obj_ids = [first_content + 1 + i * 2 for i in range(n_pages)]
        content_obj_ids = [first_content + i * 2 for i in range(n_pages)]
        pages_obj = 2
        catalog_obj = 1

        objects: dict[int, bytes] = {}
        objects[catalog_obj] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode()
        kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
        objects[pages_obj] = f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode()
        objects[font_obj] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

        for page_lines, cid, pid in zip(pages, content_obj_ids, page_obj_ids):
            parts = ["BT /F1 10 Tf 40 820 Td 14 TL"]
            for i, line in enumerate(page_lines):
                safe = self._pdf_escape(line[:110])
                parts.append(f"({safe}) Tj" if i == 0 else f"T* ({safe}) Tj")
            parts.append("ET")
            stream = "\n".join(parts)
            objects[cid] = f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream".encode(
                "latin-1", errors="replace"
            )
            objects[pid] = (
                f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 612 792] "
                f"/Contents {cid} 0 R /Resources << /Font << /F1 {font_obj} 0 R >> >> >>"
            ).encode()

        max_id = max(objects)
        out = bytearray(b"%PDF-1.4\n")
        offsets = {0: 0}
        for oid in range(1, max_id + 1):
            offsets[oid] = len(out)
            out.extend(f"{oid} 0 obj\n".encode("ascii"))
            out.extend(objects[oid])
            out.extend(b"\nendobj\n")
        xref_pos = len(out)
        out.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
        out.extend(b"0000000000 65535 f \n")
        for oid in range(1, max_id + 1):
            out.extend(f"{offsets[oid]:010d} 00000 n \n".encode("ascii"))
        out.extend(
            f"trailer\n<< /Size {max_id + 1} /Root {catalog_obj} 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
        )
        path.write_bytes(bytes(out))
