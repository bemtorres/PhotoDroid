# Fase 8 — i18n backend + Ajustes

## Objetivo

Persistir configuración y servir bundles i18n desde Python (`config/i18n/*.json`) sin base de datos.

## i18n backend (`backend/i18n.py`)

- Idiomas: `en` (default), `es`, `pt`, `zh-CN`, `ko`, `ja`, `de`, `fr`.
- Claves planas en `config/i18n/<lang>.json`.
- Fallback automático a `en` por clave faltante.
- Slot **`getI18nBundle()`** → `{ language, strings }` (para el frontend o herramientas).

El frontend sigue usando `frontend/js/i18n.js` para la UI en caliente; el backend expone el bundle para coherencia y testing.

## Ajustes (`config/settings.json`)

| Clave | Descripción |
|---|---|
| `language` | Idioma inicial y persistido |
| `adb_path` | Binario ADB |
| `risk_thresholds` | `{low, suspicious, high}` |
| `scan.include_system_apps` | Incluir apps de sistema |
| `scan.permission_scan_system` | Escanear permisos de sistema |
| `reports.output_dir` | Carpeta de informes |

### Slot **`saveSettings(rawJson)`**

1. Merge de claves permitidas.
2. Escribe `config/settings.json`.
3. Emite `settingsSaved` + `languageChanged`.

## Frontend — vista **Settings**

- Selector de idioma, ruta ADB, umbrales, checkboxes de scan, carpeta de reportes.
- Botón **Save settings** → `bridge.saveSettings(...)`.
- Navbar: **Settings** (icono gear).

## Verificación

```text
I18n.load en/es/... → OK · getI18nBundle JSON válido
saveSettings roundtrip → settings.json actualizado
node --check settings.js · i18n 8 idiomas sin faltantes
```

## Siguiente fase

Fase 9 — pulido y empaquetado (PyInstaller).
