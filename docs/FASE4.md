# Fase 4 — UX de progreso y eventos en vivo

## Objetivo

Que el usuario vea **qué está pasando** durante detección y escaneos, sin congelar la UI y con control para cancelar.

## Qué se implementó

### Backend (`backend/bridge.py`, `backend/workers.py`)

- Señal **`stateChanged`**: emite etapas lógicas del worker o del flujo:
  - `detecting` · `loading_apps` · `scanning_permissions` · `loading_processes` · `scanning` · `idle`
- Señal **`scanStage`**: subetapas del escaneo completo: `apps` → `permissions` → `threats` → `processes` → (UI: `done`)
- **`startScan()`** lanza `FullScanWorker` (QThread) con:
  - progreso incremental (apps 5–30, permisos 30–78, amenazas 88, procesos 100)
  - cancel cooperativo entre pasos y en el bucle de permisos
- **`cancelScan()`** (slot): pide cancel al worker; al `finished`, si estaba cancelado → estado `idle` + log.
- Los handlers intermedios (`_on_permissions`, `_on_processes`) **no** fuerzan `idle` mientras corre el escaneo completo (evita desbloquear la UI a mitad).

### Frontend (`frontend/js/app.js`, `index.html`, `scanner.js`)

| Elemento | Rol |
|---|---|
| `#state-badge` | Estado actual en el sidebar |
| `#stage-label` | Etapa i18n (`stage.*`) junto a la barra de progreso |
| `#btn-cancel-scan` | Visible y habilitado solo en `scanning` |
| `.action-btn` | Deshabilitados durante estados busy (Cancel excluido) |
| `.log-error` | Resaltado en consola para mensajes de error/fail |
| `.progress-fill` + `#progress-label` | % de avance en vivo |

- `UI.setState` → badge, botones, cancel, stage.
- `UI.setStage` → etapa del escaneo y label de progreso.
- Bind de señales en `bindScanSignals` / `bindDeviceSignals` (idempotente con flags).

### Estados busy

`detecting`, `loading_apps`, `scanning_permissions`, `loading_processes`, `scanning`.

## Verificación

- `python -m py_compile` en backend y `main.py`.
- `node --check` en `frontend/js/*.js`.
- Flujo esperado: **Start scan** → stage apps → permissions → threats → processes → done + `scanFinished`; **Cancel** → worker corta → `idle`.

## Siguiente fase

[Fase 5 — motor de amenazas](FASE5.md).
