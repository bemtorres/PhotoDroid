# Fase 9 — Pulido y empaquetado (PyInstaller)

## Objetivo

Dejar la app lista para distribuir en Windows (y punto de partida para Linux/macOS).

## Cambios

| Área | Detalle |
|---|---|
| Estados UI | `quarantining`, `exporting` deshabilitan `.action-btn` |
| Errores | Mapeados a i18n (`device.err.*`, `quarantine.*`, `report` logs) |
| ADB | Ruta absoluta en settings + fallback `COMMON_ADB_PATHS` + `CREATE_NO_WINDOW` |
| Auditoría | Cuarentena en `config/quarantine_audit.jsonl` |
| Spec | `PhotoDroid.spec` empaqueta `frontend/`, `assets/`, `config/`, `rules/` · icono `assets/PhotoDroid.ico` |

## Build (Windows)

```powershell
pip install pyinstaller
pyinstaller PhotoDroid.spec --noconfirm
# Salida: dist/PhotoDroid/PhotoDroid.exe
```

Notas:

- Incluye `QtWebEngine` (exe grande ~200–400 MB, normal con PySide6).
- El usuario sigue necesitando **ADB** (platform-tools) en el equipo destino; se configura en Settings → ADB path.
- Si se quiere un único `.exe` (`--onefile`), el arranque es más lento y hay que cuidar rutas relativas de `frontend/`.

## Verificación final

```text
py_compile backend/*.py + main.py     → OK
node --check frontend/js/*.js         → OK
i18n 8 idiomas paridad                → OK
ReportBuilder export 4 formatos       → OK
Quarantine confirmación obligatoria   → OK
```

## Roadmap posterior (no bloqueante)

- Firma de binario / instalador (Inno Setup, MSI).
- Tests automatizados (pytest) para `threat_engine`, `quarantine`, `reports`.
- iOS / wireless ADB (fuera del alcance actual USB).
