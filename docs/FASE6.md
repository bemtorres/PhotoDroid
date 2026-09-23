# Fase 6 — Cuarentena / mitigación controlada

## Objetivo

Acciones reversibles o auditables sobre apps detectadas: **deshabilitar**, **detener** y **desinstalar** (solo terceros), siempre con **confirmación en UI** y **log de auditoría**.

## Backend (`backend/quarantine.py`)

| Acción | Comando ADB | Notas |
|---|---|---|
| `disable` | `pm disable-user --user 0 <pkg>` | Reversible con `enable` |
| `enable` | `pm enable <pkg>` | Restaura app deshabilitada |
| `force_stop` | `am force-stop <pkg>` | No desinstala |
| `uninstall` | `pm uninstall <pkg>` | **Bloqueado** si el paquete es de sistema |

- `QuarantineManager.apply(..., confirmed=True)` exige `confirmation_required` si falta confirmación.
- Auditoría JSONL: `config/quarantine_audit.jsonl` (`timestamp`, `action`, `package`, `serial`, `ok`, `output`, `system`).

## Bridge

| Señal / Slot | Uso |
|---|---|
| `quarantineAction(action, package, confirmed)` | Aplica acción en `QuarantineWorker` (QThread) |
| `listQuarantineLog()` | Devuelve últimas 50 entradas |
| `quarantineReady` / `quarantineError` / `quarantineLogReady` | UI |

Estado UI: `quarantining` (botones busy).

## Frontend

- Vista **Threats**: columna **Actions** con *Stop / Disable / Uninstall* por hallazgo.
- **Modal de confirmación** (`#confirm-modal`) antes de cualquier acción.
- Panel **Quarantine / mitigation** con log de auditoría (`#quarantine-log-table`).
- i18n: claves `quarantine.*`, `modal.*`, `table.actions|time|action|result`, `stage.quarantining` en **8 idiomas**.

## Verificación

```text
py_compile backend/quarantine.py backend/workers.py backend/bridge.py  → OK
node --check frontend/js/{quarantine,threats,app}.js                   → OK
uninstall sobre paquete de sistema → QuarantineError system_app_blocked
```

## Siguiente fase

Fase 7 — reportes JSON/CSV/HTML/PDF.
