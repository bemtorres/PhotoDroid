# Fase 5 — Motor de amenazas + vista Threats

## Objetivo

Puntuar el riesgo del dispositivo con **reglas JSON explicables** (sin BD) y mostrarlo en la app.

## Reglas (`rules/`)

| Archivo | Contenido |
|---|---|
| `heuristics.json` | Pesos por permiso, `flag_weights` (overlay/accessibility), `dangerous_count_weight`, `system_score_factor` (×0.4 apps de sistema), `cap` 100, `min_finding_score` 15 |
| `signatures.json` | `known_packages`, `package_patterns` (regex), `installer_rules` (sideload/unknown) |

Umbrales en `config/settings.json → risk_thresholds`: `{low:20, suspicious:50, high:75}` → niveles app: `low` / `suspicious` / `high` / `critical` (`score ≥ high`).

## Motor (`backend/threat_engine.py`)

- `ThreatEngine(rules_dir, thresholds).evaluate(apps, permissions, services)` → dict:
  - `risk_score`, `risk_level`, `threat_count`, `findings[]` (package, score, level, reasons, permissions, flags, system), `services` (overlay/a11y), `thresholds`, `generated_at`
- Cada hallazgo incluye `reasons[]` con `code` / `weight` / `detail` (auditable).
- Fallback a pesos por defecto si falta algún JSON.

## Integración

| Capa | Cambio |
|---|---|
| `FullScanWorker` / `PermissionScanWorker` | Emite **`threatsReady(report)`** + stage `threats` |
| `Bridge` | Señal `threatsReady`, caché `_last_*`, slot **`reevaluateThreats()`**, umbrales desde settings |
| `frontend/js/threats.js` | `renderThreats`, badges de nivel, botón Re-evaluate |
| `frontend/index.html` | Vista `#view-threats`: score, findings, servicios, tabla |
| `i18n.js` | Claves `threats.*`, `risk.*`, `stage.*`, `nav.threats`, `table.level/reasons` en **8 idiomas** |

## Flujo

1. **Start scan** o **Scan permissions** → engine en el worker → `threatsReady` → UI.
2. Vista **Threats** en el nav: tarjetas de riesgo/hallazgos + tabla ordenada por score.
3. **Re-evaluate** → `bridge.reevaluateThreats()` con la última caché de apps/permisos/servicios (sin ADB extra).

## Verificación

```text
ThreatEngine dummy: risk 100 critical, threats ≥1  → OK
py_compile backend/*.py + main.py                 → OK
node --check frontend/js/*.js                     → OK
i18n: 8 idiomas × 66 claves, sin faltantes        → OK
Tailwind local: clases nuevas incluidas           → OK
```

## Siguiente fase

Fase 6 — cuarentena / mitigación controlada.
