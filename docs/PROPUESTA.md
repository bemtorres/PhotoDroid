# PhotoDroid — Propuesta Técnica

Herramienta de escritorio para análisis, diagnóstico y limpieza controlada de dispositivos Android conectados por USB.

---

## 1. Resumen

Aplicación de escritorio **Python + PySide6** que renderiza una UI web moderna (HeroUI + Tailwind) dentro de `QWebEngineView`. La comunicación frontend↔backend se hace con `QWebChannel`; todo el trabajo pesado (ADB, escaneo, análisis) corre en hilos `QThread` para no bloquear la interfaz. Sin base de datos: configuración, reglas e i18n en archivos **JSON**.

## 2. Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+, PySide6, subprocess (ADB) |
| Frontend | HTML5, Tailwind CSS, HeroUI, JavaScript |
| Puente JS↔Python | QWebChannel + QWebEngineView |
| Dispositivo | Android Debug Bridge (ADB) |
| Persistencia | JSON (config, reglas, firmas, i18n) |
| Hilos | QThread / señales Qt para escaneos en tiempo real |

## 3. Arquitectura

```
┌─────────────────────────────────────────────┐
│  Ventana PySide6 (QWebEngineView)          │
│  ┌───────────────────────────────────────┐  │
│  │ Frontend: HeroUI + Tailwind + JS      │  │
│  │  app.js / dashboard.js / scanner.js   │  │
│  └──────────────┬────────────────────────┘  │
│                 │ QWebChannel                │
│  ┌──────────────▼────────────────────────┐  │
│  │ Backend Python (expuesto a JS)        │  │
│  │  señales Qt → actualizaciones RT      │  │
│  └──────────────┬────────────────────────┘  │
└─────────────────┼───────────────────────────┘
                  │ subprocess
        ┌─────────▼─────────┐
        │  ADB → dispositivo │
        └───────────────────┘
```

**Principios:**
- JS llama a funciones Python expuestas vía `QWebChannel`.
- Python emite señales (logs, progreso, estado) que JS recibe en tiempo real.
- Ningún comando ADB se ejecuta en el hilo de UI.

## 4. Estructura del proyecto

```
photo-droid/
├── main.py                     # Ventana, QWebEngineView, QWebChannel
├── config/
│   ├── settings.json           # Configuración general (idioma, paths, ADB)
│   └── i18n/
│       ├── en.json             # Inglés (por defecto)
│       ├── es.json             # Español
│       ├── pt.json             # Portugués
│       ├── zh.json             # Chino
│       ├── ko.json             # Coreano
│       ├── ja.json             # Japonés
│       ├── de.json             # Alemán
│       └── fr.json             # Francés
├── backend/
│   ├── adb_manager.py          # Detección de dispositivos, ejecución/captura ADB
│   ├── device_manager.py       # Modelo, Android, serie, estado, batería
│   ├── app_scanner.py          # Apps instaladas y paquetes
│   ├── permission_scanner.py   # Permisos y servicios (Accessibility, Overlay…)
│   ├── process_scanner.py      # Procesos activos en tiempo real
│   ├── threat_engine.py        # Motor heurístico + reglas JSON → riesgo
│   ├── quarantine.py           # Mitigación: deshabilitar, detener, desinstalar
│   ├── reports.py              # Reportes JSON, CSV, HTML, PDF
│   └── i18n.py                 # Carga/selector de idioma desde JSON
├── frontend/
│   ├── index.html              # Dashboard HeroUI + Tailwind local
│   ├── css/app.css
│   └── js/
│       ├── app.js              # Conexión QWebChannel + i18n
│       ├── dashboard.js        # Vistas y eventos
│       └── scanner.js          # Actualizaciones de escaneo en RT
├── assets/
│   └── tailwind.css            # Build local de Tailwind (sin CDN)
├── rules/
│   ├── heuristics.json         # Puntuación de amenazas
│   └── signatures.json         # Firmas conocidas
├── reports/                    # Salida de reportes
└── requirements.txt
```

## 5. Módulos clave

### 5.1 `adb_manager.py`
- Detectar binario ADB (PATH o ruta en `settings.json`).
- `run(command, timeout)` → ejecuta subprocess, captura stdout/stderr, devuelve resultado estructurado.
- Auto-arranque del servidor ADB y detección de dispositivos (`devices -l`).

### 5.2 `device_manager.py`
- Extrae: modelo, marca, versión Android, SDK, serie, estado (device/offline), batería, almacenamiento.
- Señal `deviceStatusChanged` hacia el frontend.

### 5.3 Escáneres
- **app_scanner**: `pm list packages -f -3` / `-s`, flags (sistema/tercero), rutas APK.
- **permission_scanner**: `dumpsys package` → permisos peligrosos, servicios de accesibilidad, apps sobre otras ventanas.
- **process_scanner**: `ps -A` / `top` en intervalo configurable → tabla en tiempo real.

### 5.4 `threat_engine.py`
- Carga `heuristics.json` y `signatures.json`.
- Combina señales (permisos críticos + firmas + comportamiento) → score 0–100.
- Niveles: **Bajo**, **Sospechoso**, **Alto**, **Crítico**.
- Devuelve explicación por hallazgo (auditable, sin caja negra).

### 5.5 `quarantine.py` (controlado)
- Acciones siempre con confirmación en UI: `pm disable-user`, `am force-stop`, `pm uninstall` (solo apps de terceros).
- Log de cada acción para auditoría y posible reversión (`pm enable`).

### 5.6 `reports.py`
- Exporta: **JSON**, **CSV**, **HTML** (estilo dashboard) y **PDF** (generación desde HTML).
- Carpeta `reports/` con nombre `informe_<serie>_<fecha>`.

## 6. i18n (JSON, sin BD)

- Idioma por defecto: **en**; soporte: es, pt, zh, ko, ja, de, fr.
- Claves planas: `{"dashboard.title": "...", "scan.start": "..."}`.
- `i18n.py` carga el JSON del idioma activo (de `settings.json`) y lo expone al frontend via QWebChannel.
- Cambio de idioma en caliente: JS solicita `setLanguage(code)` → Python responde con el bundle completo → JS actualiza textos sin reiniciar.

## 7. UI (HeroUI + Tailwind)

Dashboard estilo ciberseguridad con:
- **Header**: estado de conexión USB, selector de idioma, tema claro/oscuro.
- **Tarjetas**: dispositivo conectado, nivel de riesgo global, nº apps, nº amenazas.
- **Vistas**: Dashboard · Apps · Permisos · Procesos · Amenazas · Reportes · Ajustes.
- **Tablas** paginadas (HeroUI), **barras de progreso** de escaneo, **modales** de confirmación para acciones destructivas.
- **Consola de logs** en tiempo real (streaming por señales Qt).

## 8. Plan de desarrollo (MVP + fases)

| Fase | Entregable | Esfuerzo est. |
|------|-----------|---------------|
| **1** | `main.py` + QWebEngineView + QWebChannel + `index.html` base HeroUI | ✅ |
| **2** | `adb_manager.py` + `device_manager.py`: detección USB e info del equipo | ✅ |
| **3** | Escáneres: apps, permisos, procesos | ✅ |
| **4** | Wiring frontend↔backend: botones, logs y progreso en tiempo real | ✅ |
| **5** | `threat_engine.py` + `rules/*.json` + vista de amenazas | ✅ |
| **6** | `quarantine.py` + modales de confirmación + auditoría | ✅ |
| **7** | `reports.py` (JSON/CSV/HTML/PDF) | ✅ |
| **8** | i18n completo (8 idiomas) + `settings.json` + ajustes | ✅ |
| **9** | Pulido UI, manejo de errores, empaquetado (PyInstaller) | ✅ |

**MVP mínimo (fases 1–4):** ventana + detección de dispositivo + listados + UI en vivo.

## 9. Riesgos y mitigación

| Riesgo | Mitigación |
|--------|-----------|
| ADB no instalado o fuera de PATH | Detección en settings + guía de instalación en UI |
| Dispositivo sin depuración USB | Modal con instrucciones paso a paso |
| UI congelada por comandos lentos | Todo en QThread; timeouts en subprocess |
| Acciones destructivas accidentales | Confirmación obligatoria + log de auditoría |
| Tailwind/CDN caído o sin internet | Tailwind vendorizado en `assets/tailwind.css` (build local) |
| Permisos de `dumpsys` variables entre Android | Múltiples fallbacks por versión SDK |

## 10. Criterios de aceptación del MVP

1. Detecta automáticamente el dispositivo Android conectado y muestra modelo/versión/estado.
2. Lista apps, permisos y procesos sin bloquear la UI.
3. Escaneo con barra de progreso y logs en tiempo real.
4. Nivel de riesgo calculado con reglas JSON explicables.
5. Selector de idioma funcional (en/es al menos en MVP; resto en fase 8).
6. Exporta al menos un reporte JSON y HTML.

---

**Siguiente paso sugerido:** empezar por la **Fase 1** (`main.py` + `index.html` + puente QWebChannel) para tener el esqueleto navegable e ir conectando módulos.
