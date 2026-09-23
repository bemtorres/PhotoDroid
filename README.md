# PhotoDroid

Herramienta de **escritorio** para **analizar, diagnosticar y limpiar de forma controlada** dispositivos Android conectados por USB (ADB), con interfaz tipo dashboard de ciberseguridad.

> Estado actual: **Fases 1–9** (ventana, detección, scanners, UX en vivo, motor de amenazas, cuarentena, reportes, ajustes/i18n y empaquetado).

---

## ¿De qué se trata?

PhotoDroid conecta tu PC a un teléfono Android mediante **ADB** y te muestra, en una sola ventana:

- **Dispositivo conectado**: modelo, Android, serie, batería.
- **Aplicaciones instaladas**: paquete, tipo (usuario/sistema), ruta APK.
- **Permisos peligrosos**: SMS, Accessibility, Overlay, instalación de apps, etc., con puntuación de riesgo.
- **Procesos activos** en tiempo real.
- **Motor de amenazas**: puntuación de riesgo 0–100 con hallazgos explicables (permisos, flags, firmas).
- **Cuarentena / mitigación**: deshabilitar, detener o desinstalar apps de terceros con confirmación y auditoría.
- **Reportes**: exporta JSON, CSV, HTML y PDF del último análisis.
- **Ajustes**: idioma, ruta ADB, umbrales de riesgo y opciones de escaneo.

No usa base de datos: la configuración y las reglas viven en **JSON**.

---

## Cómo funciona (arquitectura)

```
┌──────────────────────────────────────────────────────────┐
│  Ventana PySide6 (QWebEngineView)                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Frontend: HTML + Tailwind + JS (estilo HeroUI)    │  │
│  │  vistas: Dashboard · Scanner · Threats · Apps · Reports│
│  └──────────────▲──────────────────────┬──────────────┘  │
│                 │ QWebChannel          │ llamadas JS     │
│  ┌──────────────┴──────────────────────▼──────────────┐  │
│  │  Bridge Python (señales/Slots)                     │  │
│  │  adb · device · apps · permissions · processes     │  │
│  │  threat_engine · cancel / re-evaluate              │  │
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

# 4. Comprobar ADB (ver abajo)
adb devices
```

### 4. ADB en PATH o `adb_path`

PhotoDroid no “inventa” el teléfono: usa el binario **`adb`** (Android Debug Bridge) para hablar con el equipo por USB. Necesitas que el sistema (o la app) sepa **dónde está ese ejecutable**.

#### Qué es el PATH

El `PATH` es la lista de carpetas donde Windows/Linux/macOS buscan un comando cuando escribes `adb` en la terminal.

- Si ADB está en el PATH → basta `adb devices`
- Si **no** está → la terminal responde algo como *«adb no se reconoce como un comando interno…»* y PhotoDroid puede fallar al detectar el dispositivo

#### Opción A — ADB en el PATH (recomendada)

1. Descarga/instala [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) (o usa el de Android Studio).
2. Ruta habitual en Windows:
   `C:\Users\<tu-usuario>\AppData\Local\Android\Sdk\platform-tools`
3. Comprueba desde una **terminal nueva**:

```bash
adb version
adb devices
```

- `adb version` imprime la versión → el PATH está bien.
- `adb devices` debe listar tu equipo con `device` (no vacío, no `unauthorized`).

Si no funciona, añade esa carpeta a las **variables de entorno → Path** del sistema y abre la terminal otra vez.

#### Opción B — Ruta completa en PhotoDroid (sin tocar el PATH)

Si no quieres tocar el PATH, PhotoDroid acepta la ruta al ejecutable en `config/settings.json`:

```json
{
  "adb_path": "adb"
}
```

| Valor | Cuándo sirve |
|---|---|
| `"adb"` (por defecto) | ADB ya está en el PATH |
| Ruta absoluta | ADB **no** está en el PATH |

Ejemplo en Windows:

```json
{
  "adb_path": "C:\\Users\\tu-usuario\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe"
}
```

> En JSON hay que escapar las barreras invertidas (`\\`).

La app lee `settings.json → adb_path` y se lo pasa a cada worker de escaneo. Si tampoco encuentra ahí el binario, prueba rutas comunes o muestra: *«ADB not found… set adb_path»*.

#### ¿Qué significa `adb devices`?

```text
List of devices attached
XXXXXXXX    device
```

| Estado | Significado |
|---|---|
| `device` | Listo: PhotoDroid puede escanear |
| vacío | Cable, depuración USB o driver |
| `unauthorized` | Acepta el diálogo en el móvil |
| `offline` | Reconecta o reinicia `adb kill-server && adb start-server` |

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
3. O bien **Start scan** en el Dashboard → escaneo completo (apps → permisos → amenazas → procesos) con barra de progreso, etapas, **Cancel** y log.
4. Abre **Threats** → score de riesgo, hallazgos y servicios activos (A11y / Overlay); **Re-evaluate** recalcula con los últimos datos en caché. Desde la tabla puedes **Stop / Disable / Uninstall** (siempre con modal de confirmación) y ver la auditoría.
5. Abre **Reports** → exporta el último análisis a **JSON / CSV / HTML / PDF**.
6. Abre **Settings** → idioma, `adb_path`, umbrales de riesgo y opciones de escaneo → **Save settings**.
7. Cambia el idioma en el selector de la cabecera (en, es, pt, zh-CN, ko, ja, de, fr).

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
│   ├── threat_engine.py        # Motor heurístico + firmas (Fase 5)
│   ├── quarantine.py           # Mitigación controlada + auditoría (Fase 6)
│   ├── reports.py              # JSON / CSV / HTML / PDF (Fase 7)
│   ├── i18n.py                 # Bundles i18n backend (Fase 8)
│   └── workers.py              # QThread workers (+ cancel de escaneo)
├── frontend/
│   ├── index.html              # Layout del dashboard (usa ../assets/tailwind.css)
│   ├── css/app.css
│   └── js/
│       ├── i18n.js             # Traducciones (8 idiomas)
│       ├── app.js              # QWebChannel + UI helpers
│       ├── dashboard.js        # Vistas, detección de dispositivo
│       ├── scanner.js          # Tablas y escaneo
│       ├── threats.js          # Vista Amenazas (Fase 5)
│       ├── quarantine.js       # Acciones + modal (Fase 6)
│       ├── reports.js          # Exportar informes (Fase 7)
│       └── settings.js         # Ajustes (Fase 8)
├── assets/
│   ├── PhotoDroid.ico           # Icono de ventana / .exe (PyInstaller)
│   ├── PhotoDroid_*.png         # Logos (favicon, sidebar, landing)
│   └── tailwind.css             # Tailwind build local (sin CDN)
├── docs/                       # Documentación (PROPUESTA, fases)
├── reports/                    # Salida de reportes (Fase 7)
├── rules/                      # heuristics.json / signatures.json (Fase 5)
└── PROPUESTA.md                # (ver docs/PROPUESTA.md)
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
| `cancelScan()` | Cancela el escaneo en curso |
| `reevaluateThreats()` | Recalcula el motor con la última caché |
| `quarantineAction(action, package, confirmed)` | Mitigación (disable / force_stop / uninstall) |
| `listQuarantineLog()` | Auditoría de cuarentena |
| `exportReport(fmt)` | Exporta informe `json` / `csv` / `html` / `pdf` |
| `listReports()` | Lista informes en `reports/` |
| `saveSettings(json)` | Persiste `config/settings.json` |
| `getI18nBundle()` | Bundle i18n del backend |

**Python → JS (señales)**

`log`, `progress`, `stateChanged`, `deviceFound`, `deviceError`, `appsReady`, `permissionsReady`, `servicesReady`, `processesReady`, `threatsReady`, `scanStage`, `scanFinished`, `scanError`, `quarantineReady`, `quarantineError`, `quarantineLogReady`, `reportReady`, `reportError`, `settingsSaved`

---

## Roadmap

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Ventana + frontend + QWebChannel | ✅ |
| 2 | Detección ADB e info del dispositivo | ✅ |
| 3 | Scanners: apps, permisos, procesos | ✅ |
| 4 | UX de progreso/eventos en vivo | ✅ |
| 5 | `threat_engine` + `rules/*.json` + vista Amenazas | ✅ |
| 6 | Cuarentena / mitigación | ✅ |
| 7 | Reportes JSON/CSV/HTML/PDF | ✅ |
| 8 | i18n completo + settings | ✅ |
| 9 | Pulido y empaquetado (PyInstaller) | ✅ |

---

## Documentación

- [`docs/PROPUESTA.md`](docs/PROPUESTA.md) — propuesta técnica completa
- [`docs/FASE4.md`](docs/FASE4.md) — UX en vivo (progreso, estados, cancel)
- [`docs/FASE5.md`](docs/FASE5.md) — motor de amenazas + vista Threats
- [`docs/FASE6.md`](docs/FASE6.md) — cuarentena / mitigación
- [`docs/FASE7.md`](docs/FASE7.md) — reportes JSON/CSV/HTML/PDF
- [`docs/FASE8.md`](docs/FASE8.md) — i18n backend + ajustes
- [`docs/FASE9.md`](docs/FASE9.md) — pulido y PyInstaller
- [`_www/`](_www/) — landing multiidioma de la app

---

## Empaquetado (PyInstaller)

```powershell
pip install pyinstaller
pyinstaller PhotoDroid.spec --noconfirm
# dist/PhotoDroid/PhotoDroid.exe
```

El destino necesita **ADB** (platform-tools); se configura en Settings → ADB path.

---

## Solución de problemas

| Problema | Solución |
|---|---|
| `ADB not found` | Instala platform-tools o pon la ruta en `adb_path` |
| `no_devices` | Activa depuración USB y reconecta |
| `unauthorized` | Acepta el diálogo en el teléfono |
| Ventana en blanco o sin estilos | Revisa que existan `frontend/index.html` y `assets/tailwind.css` (CSS local, sin CDN) |
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
