# PhotoDroid

Herramienta de **escritorio** para **analizar, diagnosticar y limpiar de forma controlada** dispositivos Android conectados por USB (ADB), con interfaz tipo dashboard de ciberseguridad.

> Estado actual: **MVP Fases 1–3** (ventana + detección de dispositivo + scanners de apps/permisos/procesos).

---

## ¿De qué se trata?

PhotoDroid conecta tu PC a un teléfono Android mediante **ADB** y te muestra, en una sola ventana:

- **Dispositivo conectado**: modelo, Android, serie, batería.
- **Aplicaciones instaladas**: paquete, tipo (usuario/sistema), ruta APK.
- **Permisos peligrosos**: SMS, Accessibility, Overlay, instalación de apps, etc., con puntuación de riesgo.
- **Procesos activos** en tiempo real.
- (Previsto) Motor de amenazas, cuarentena/limpieza y reportes.

No usa base de datos: la configuración y las reglas viven en **JSON**.

---

## Cómo funciona (arquitectura)

```
┌──────────────────────────────────────────────────────────┐
│  Ventana PySide6 (QWebEngineView)                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Frontend: HTML + Tailwind + JS (estilo HeroUI)    │  │
│  │  vistas: Dashboard · Scanner · Apps · Reports       │  │
│  └──────────────▲──────────────────────┬──────────────┘  │
│                 │ QWebChannel          │ llamadas JS     │
│  ┌──────────────┴──────────────────────▼──────────────┐  │
│  │  Bridge Python (señales/Slots)                     │  │
│  │  adb · device · apps · permissions · processes     │  │
│  │  Workers en QThread (la UI nunca se congela)       │  │
│  └───────────────────────┬────────────────────────────┘  │
└──────────────────────────┼───────────────────────────────┘
                           │ subprocess (adb)
                           ▼
                    Android (USB / depuración)
```

1. El frontend JS invoca slots del objeto `bridge` (p. ej. `bridge.startScan()`).
2. Python lanza un **`QThread`** que ejecuta comandos ADB.
3. El worker emite **señales** (`appsReady`, `progress`, `log`…) que actualizan la UI en vivo.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.10+, PySide6 |
| Frontend | HTML5, Tailwind CSS, JavaScript (componentes estilo HeroUI) |
| Puente | `QWebEngineView` + `QWebChannel` |
| Dispositivos | Android Debug Bridge (ADB) |
| Config / reglas | JSON (`config/`, `rules/`) — sin base de datos |
| i18n | 8 idiomas: en (default), es, pt, zh-CN, ko, ja, de, fr |

---

## Requisitos

- **Python** 3.10 o superior (probado en 3.13)
- **ADB** (Android platform-tools):
  - Windows: suele estar en `%LOCALAPPDATA%\Android\Sdk\platform-tools`
  - O en el `PATH` del sistema; si no, se configura `adb_path` en `settings.json`
- **Dispositivo Android** con **depuración USB** activada y autorizado el equipo en el diálogo del teléfono
- `PySide6` (se instala desde `requirements.txt`)

---

## Instalación

```bash
# 1. Clonar o entrar al directorio del proyecto
cd PhotonDroid

# 2. Entorno virtual (recomendado)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. ADB en PATH (o editar config/settings.json → "adb_path")
adb devices
```

---

## Uso

```bash
python main.py
```

### Flujo típico

1. Conecta el Android por USB y acepta la depuración.
2. Pulsa **Detect device** (cabecera) → aparecen modelo, Android y serie.
3. Abre **Scanner** en el menú lateral:
   - **Load apps** → inventario de paquetes
   - **Scan permissions** → permisos peligrosos + Accessibility/Overlay
   - **Load processes** → procesos activos
4. O bien **Start scan** en el Dashboard → escaneo completo (apps → permisos → procesos) con barra de progreso y log.
5. Cambia el idioma en el selector de la cabecera (en, es, pt, zh-CN, ko, ja, de, fr).

---

## Estructura del proyecto

```
PhotonDroid/
├── main.py                     # Ventana, QWebEngineView, QWebChannel
├── requirements.txt
├── config/
│   └── settings.json           # Idioma, adb_path, umbrales, opciones de scan
├── backend/
│   ├── bridge.py               # Objeto expuesto a JS (slots + señales)
│   ├── adb_manager.py          # Ejecución y parseo de comandos ADB
│   ├── device_manager.py       # Info del dispositivo (modelo, Android, batería…)
│   ├── app_scanner.py          # Apps instaladas
│   ├── permission_scanner.py   # Permisos y servicios peligrosos
│   ├── process_scanner.py      # Procesos activos
│   └── workers.py              # QThread workers
├── frontend/
│   ├── index.html              # Layout del dashboard
│   ├── css/app.css
│   └── js/
│       ├── i18n.js             # Traducciones (8 idiomas)
│       ├── app.js              # QWebChannel + UI helpers
│       ├── dashboard.js        # Vistas, detección de dispositivo
│       └── scanner.js          # Tablas y escaneo
├── docs/                       # Documentación por fase
├── reports/                    # Salida de reportes (Fase 7)
├── rules/                      # heuristics.json / signatures.json (Fase 5)
└── PROPUESTA.md                # Propuesta técnica
```

---

## Configuración (`config/settings.json`)

| Clave | Descripción |
|---|---|
| `language` | Idioma inicial (`en`, `es`, `pt`, `zh-CN`, `ko`, `ja`, `de`, `fr`) |
| `adb_path` | Ruta o nombre del binario `adb` |
| `risk_thresholds` | Umbrales de riesgo (Fase 5): low / suspicious / high |
| `scan.include_system_apps` | Incluir apps del sistema en el inventario |
| `scan.permission_scan_system` | Analizar también permisos de apps de sistema |
| `reports.output_dir` | Carpeta de reportes |

---

## API del puente (JS ↔ Python)

**JS → Python (slots)**

| Slot | Función |
|---|---|
| `detectDevice()` | Detecta el dispositivo USB |
| `listApps()` | Lista aplicaciones |
| `scanPermissions()` | Analiza permisos (requiere `listApps` antes) |
| `listProcesses()` | Lista procesos |
| `startScan()` | Escaneo completo |

**Python → JS (señales)**

`log`, `progress`, `stateChanged`, `deviceFound`, `deviceError`, `appsReady`, `permissionsReady`, `servicesReady`, `processesReady`, `scanStage`, `scanFinished`, `scanError`

---

## Roadmap

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Ventana + frontend + QWebChannel | ✅ |
| 2 | Detección ADB e info del dispositivo | ✅ |
| 3 | Scanners: apps, permisos, procesos | ✅ |
| 4 | UX de progreso/eventos en vivo | ⏳ |
| 5 | `threat_engine` + `rules/*.json` | ⏳ |
| 6 | Cuarentena / mitigación | ⏳ |
| 7 | Reportes JSON/CSV/HTML/PDF | ⏳ |
| 8 | i18n completo + settings | ✅ parcial (UI) |
| 9 | Pulido y empaquetado (PyInstaller) | ⏳ |

---

## Documentación

- [`PROPUESTA.md`](PROPUESTA.md) — propuesta técnica completa
- [`docs/FASE3.md`](docs/FASE3.md) — scanners y puente JS↔Python
- [`requerimientos.txt`](requerimientos.txt) — requerimientos originales

---

## Solución de problemas

| Problema | Solución |
|---|---|
| `ADB not found` | Instala platform-tools o pon la ruta en `adb_path` |
| `no_devices` | Activa depuración USB y reconecta |
| `unauthorized` | Acepta el diálogo en el teléfono |
| Ventana en blanco | Revisa que `frontend/index.html` exista y que el CDN de Tailwind cargue |
| UI lenta al escanear | Reduce `permission_scan_system` / usa `Start scan` con menos apps de sistema |

---

## Clonar y contribuir

```bash
git clone <url-del-repositorio> PhotonDroid
cd PhotonDroid
```

- **Issues**: bugs, ideas de mejora y fases del roadmap.
- **PRs**: bienvenidos; sigue el estilo del repo y describe el cambio.
- **i18n**: faltan textos en algún idioma → añádelos en `_www/js/i18n.js`.

---

## Licencia / Uso

**[MIT](LICENSE)** — libre para usar, copiar, modificar y distribuir, con la atribución incluida.

Herramienta de diagnóstico y limpieza **controlada**: las acciones sobre el dispositivo deben confirmarse en la UI. Úsala solo en dispositivos propios o con autorización.
