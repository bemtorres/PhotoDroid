# Fase 7 — Reportes (JSON / CSV / HTML / PDF)

## Objetivo

Exportar el estado del último análisis a archivos en `reports/`.

## Backend (`backend/reports.py`)

| Formato | Extensión | Contenido |
|---|---|---|
| `json` | `.json` | Payload completo (device, threats, apps, permissions, processes) |
| `csv` | `.csv` | Secciones aplanadas (`section,key,value`) |
| `html` | `.html` | Dashboard HTML autocontenido (tablas findings + apps) |
| `pdf` | `.pdf` | PDF de texto mínimo **sin dependencias extra** (multi-página) |

Nombre: `informe_<serial>_<YYYYMMDD_HHMMSS>.<ext>`.

`ReportBuilder.build_payload(...)` + `export(payload, fmt)`.

## Bridge

| Slot / Señal | Uso |
|---|---|
| `exportReport(fmt)` | `ExportReportWorker` en QThread |
| `listReports()` | Lista `informe_*` del `output_dir` |
| `reportReady` / `reportError` | UI |

Usa caché: `_last_device`, `_last_apps`, `_last_permissions`, `_last_processes`, `_last_threats`, `_last_services`, `_last_summary`.

Estado UI: `exporting`.

## Frontend

- Vista **Reports**: botones JSON · CSV · HTML · PDF + tabla de ficheros generados.
- i18n: `reports.*`, `table.file|size`, `stage.exporting` en 8 idiomas.

## Verificación

```text
ReportBuilder dummy → json/csv/html/pdf en reports/  → OK
py_compile backend/reports.py + bridge/workers       → OK
node --check frontend/js/reports.js                  → OK
```

## Siguiente fase

Fase 8 — i18n backend + ajustes.
