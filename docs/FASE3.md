# Fase 3 — Scanners (apps, permisos, procesos)

## Objetivo

Listar aplicaciones instaladas, analizar permisos/servicios peligrosos y leer procesos activos por ADB, sin congelar la UI (todo en `QThread`).

## Módulos backend

| Archivo | Responsabilidad |
|---|---|
| `backend/app_scanner.py` | `pm list packages -f -3/-0` → `InstalledApp` (package, apk_path, system) |
| `backend/permission_scanner.py` | `dumpsys package` + Accessibility (`settings`) + Overlay (`appops`) → `AppPermissions` con `risk_score` |
| `backend/process_scanner.py` | `ps -A` → `ProcessEntry` (pid, ppid, user, name) |
| `backend/workers.py` | `AppListWorker`, `PermissionScanWorker`, `ProcessListWorker`, `FullScanWorker` |

### Señales de riesgo de permisos

- Lista `DANGEROUS_PERMISSIONS` (SMS, Accessibility, Overlay, install packages…)
- Flags: `overlay`, `accessibility`
- `risk_score` = 8 × permisos peligrosos + 20 (overlay) + 25 (a11y), tope 100

### Config (`config/settings.json`)

```json
"scan": {
  "include_system_apps": true,
  "permission_scan_system": false
}
```

- `include_system_apps`: incluir paquetes `-0` en la lista de apps.
- `permission_scan_system`: si `false`, el análisis de permisos omite paquetes del sistema (más rápido).

## Puente JS ↔ Python

| Slot JS | Señales Python |
|---|---|
| `bridge.listApps()` | `appsReady(list)` |
| `bridge.scanPermissions()` | `permissionsReady(list)`, `servicesReady(dict)` |
| `bridge.listProcesses()` | `processesReady(list)` |
| `bridge.startScan()` | `appsReady` → `permissionsReady` → `processesReady` + `scanStage` + `scanFinished` / `scanError` + `progress` |

`scanPermissions` requiere que `listApps` (o un `startScan`) se haya ejecutado antes (guarda `_last_packages`).

## Frontend

- Vistas: `#view-dashboard`, `#view-scanner`, `#view-apps`, `#view-reports`
- Scanner con pestañas: Apps / Permissions / Processes (tablas)
- Stats: `#stat-apps`, `#stat-risky`, `#stat-procs`
- Logs espejo en dashboard y scanner
- i18n: claves `scanner.*`, `table.*`, `apps.*`, `reports.*` en 8 idiomas

## Botones

1. **Detect device** (header) → `detectDevice`
2. **Load apps** → `listApps`
3. **Scan permissions** → `scanPermissions`
4. **Load processes** → `listProcesses`
5. **Start scan** (dashboard) → `startScan` (flujo completo 1/3→3/3)

## Verificación

```bash
python -m py_compile backend/*.py main.py
python main.py
```

Sin dispositivo: errores `no_devices` / `no_permissions` en el log.

## Siguiente fase

- **Fase 4**: conectar eventos restantes, progreso en tiempo real en toda la UI  
- **Fase 5**: `threat_engine` + `rules/heuristics.json` (score global Bajo/Sospechoso/Alto/Crítico)
