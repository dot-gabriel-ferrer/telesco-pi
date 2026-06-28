# Telesco-Pi — Plan de Desarrollo por Sesiones

> **Instrucciones de uso:** Cada sección es un prompt independiente y autocontenido para una sesión de agente. Cópialo completo y pégalo directamente. El hardware físico (montura SkyWatcher AZ-Go2 WiFi + cámara Player One Mars M USB 3.0) está conectado y disponible para pruebas reales.

---

## Estado actual del repositorio (resumen para todos los prompts)

```
Repositorio: dot-gabriel-ferrer/telesco-pi
Stack: Python 3.11 + FastAPI backend / React 18 + TypeScript + Vite frontend (PWA)
Hardware objetivo: Raspberry Pi 5 + SkyWatcher AZ-Go2 WiFi + Player One Mars M USB 3.0

Estado implementado:
- Backend FastAPI base completo (apps/backend/app/main.py, api/, core/)
- Simulator drivers completos: SimulatedMountDriver, SimulatedCameraDriver (services/simulator/drivers.py)
- Stubs de hardware real: AZGo2MountDriverStub, PlayerOneMarsMCameraDriverStub (libs/devices/stubs.py)
- Interfaces de dispositivos: MountDriver, CameraDriver (libs/devices/interfaces.py)
- API REST: /devices, /sessions, /astronomy/*, /health, /system (apps/backend/app/api/routes/)
- WebSocket: /api/v1/ws (apps/backend/app/api/routes/ws.py)
- Motor astronómico modular: libs/astronomy/{catalogs,visibility,planner,calibration,solving,orbital,processing,pointing,jobs}
- Frontend React base: App.tsx, páginas básicas (Dashboard, Control, Capture, Plan, Files)
- Frontend store: Zustand (appStore.ts), TanStack Query, API client (src/api/client.ts)
- Tests unitarios de astronomía: tests/unit/astronomy/

NO implementado aún:
- Driver real de montura (AZ-Go2 SynScan WiFi TCP)
- Driver real de cámara (Player One Mars M SDK Linux ARM64)
- Tests de hardware (tests/hardware/ está vacío)
- Scripts de despliegue Raspberry Pi (infra/scripts/ está vacío)
- Servicios systemd (infra/systemd/ pendiente)
- Frontend páginas secundarias (Dispositivos, Diagnóstico, Ajustes, Simulador, Onboarding)
- Implementación completa de pipelines de astronomía (framework existe, lógica pendiente)
- Endpoint /devices/mount/park (llamado desde frontend pero no existe en backend)
```

---

## SESIÓN 1 — Driver real de montura SkyWatcher AZ-Go2 WiFi (SynScan)

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`  
**Hardware disponible:** Montura SkyWatcher AZ-Go2 conectada por WiFi. IP típica: 192.168.4.1 puerto TCP 11882 (SynScan Hand Controller emulation). Puede variar según configuración de red.

### Contexto

El proyecto tiene una interfaz `MountDriver` abstracta en `libs/devices/interfaces.py` y un stub sin implementación real en `libs/devices/stubs.py` (clase `AZGo2MountDriverStub`). El simulador (`services/simulator/drivers.py`, `SimulatedMountDriver`) está completo y funciona. El registro de drivers está en `libs/devices/registry.py`.

El protocolo SynScan WiFi de SkyWatcher usa comandos ASCII sobre TCP (puerto 11882). Los comandos principales son:
- `:e1#` — Get AZ position (hex)
- `:e2#` — Get ALT position  
- `:Ka#` — Stop all movement
- `:Sr,HH:MM:SS#` + `:Sd,+DD*MM:SS#` + `:MS#` — GoTo RA/Dec
- `:Mz,XXXXX#` y `:Ma,XXXXX#` — Slew AZ/ALT steps
- `:T0#` / `:T1#` / `:T2#` — Tracking modes (off/sidereal/solar)
- `:Sts#` — Get status
- Alternativamente protocolo binario de 3 bytes para slew: `0x01 0x42 speed_byte`

Librería Python de referencia: `pyserial` (ya en requirements.txt) o conexión TCP directa con `asyncio.open_connection`.

### Tarea

Implementa el driver real de la montura AZ-Go2 en `libs/devices/az_go2.py`. Debe:

1. **Conectar** vía TCP a la IP/puerto configurables en `libs/config/settings.py` (añadir `MOUNT_HOST`, `MOUNT_PORT` si no existen)
2. **Implementar todos los métodos de `MountDriver`:**
   - `connect()` — TCP connect, enviar comando de ping/status
   - `disconnect()` — cerrar socket limpiamente
   - `get_status()` — posición actual AZ/ALT, modo tracking, health
   - `manual_slew(delta_azimuth, delta_altitude)` — slew relativo en grados
   - `goto(coordinates)` — GoTo coordenadas AZ/ALT absolutas
   - `stop()` — parar todo movimiento inmediatamente
   - `set_tracking_mode(mode)` — off/sidereal/solar
3. **Registrar** el driver en `libs/devices/registry.py` para que se active cuando `settings.device_mode == "real"`
4. **Añadir endpoint** `POST /devices/mount/park` en `apps/backend/app/api/routes/devices.py` (enviar a posición az=0, alt=90 o a posición home configurada)
5. **Tests de integración hardware** en `tests/hardware/test_mount_real.py` que prueben contra la montura real (marcar con `@pytest.mark.hardware` y skip si no hay conexión)
6. **Documentar** en `docs/architecture/device-abstractions.md` los detalles del protocolo SynScan usado

**Archivos clave a leer antes de implementar:**
- `libs/devices/interfaces.py` — interfaces abstractas
- `libs/devices/models.py` — modelos de datos (DeviceStatus, MountCoordinates, TrackingMode, etc.)
- `libs/devices/stubs.py` — stub actual (AZGo2MountDriverStub) a reemplazar
- `libs/devices/registry.py` — cómo se registran los drivers
- `libs/config/settings.py` — configuración actual (Settings con Pydantic)
- `services/simulator/drivers.py` — SimulatedMountDriver como referencia de implementación completa

**Criterios de aceptación:**
- Driver se conecta a la montura real y recibe posición AZ/ALT
- `manual_slew` mueve la montura un ángulo pequeño (ej. 0.5°) y confirma
- `stop()` para el movimiento
- `get_status()` devuelve `DeviceConnectionState.CONNECTED` y coordenadas reales
- Tests hardware pasan con `pytest -m hardware tests/hardware/test_mount_real.py`
- Simulador sigue funcionando (no romper nada)

---

## SESIÓN 2 — Driver real de cámara Player One Mars M (USB 3.0)

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`  
**Hardware disponible:** Cámara Player One Mars M conectada por USB 3.0. Dispositivo `/dev/bus/usb/...` o accesible vía SDK Player One.

### Contexto

El proyecto tiene la interfaz `CameraDriver` en `libs/devices/interfaces.py` y el stub `PlayerOneMarsMCameraDriverStub` en `libs/devices/stubs.py`. El simulador `SimulatedCameraDriver` en `services/simulator/drivers.py` genera imágenes PGM sintéticas.

**Opciones de SDK para Linux ARM64 (Raspberry Pi OS 64-bit):**
- **PlayerOne SDK oficial:** Player One Astronomy distribuye `libPlayerOneCamera.so` para Linux ARM64. Disponible en https://player-one-astronomy.com/service/sdk. El wrapper Python se puede hacer con `ctypes`.
- **Alternativa `libusb`:** Acceso directo USB con `pyusb` si el SDK no está disponible.
- **Alternativa `OpenCV VideoCapture`:** Si la cámara aparece como dispositivo V4L2 (`/dev/video0`), se puede usar `cv2.VideoCapture(0)`.
- **ZWO ASI SDK compatible:** Algunos wrappers `zwoasi` pueden funcionar con Player One en modo compatible.

**Prioridad:** Intentar SDK oficial Player One primero. Si no está disponible, usar V4L2/OpenCV como fallback. En cualquier caso, la interfaz `CameraDriver` debe cumplirse.

### Tarea

1. **Detectar** qué SDK/método está disponible en el sistema: comprobar si `/dev/video*` existe, si hay `libPlayerOneCamera.so`, si `pyusb` puede encontrar el dispositivo.
2. **Implementar** `libs/devices/playerone_mars_m.py` con la clase `PlayerOneMarsMCameraDriver(CameraDriver)`:
   - `connect()` — abrir dispositivo, verificar modelo "Mars M"
   - `disconnect()` — liberar dispositivo limpiamente
   - `get_status()` — temperatura del sensor, modo, health, ROI activo
   - `configure(CameraConfiguration)` — exposure_ms, gain, ROI width/height, bin
   - `capture_still()` — captura una imagen, devuelve `CapturedFrame` con bytes RAW o FITS
   - `start_preview()` / `stop_preview()` — streaming de frames a baja resolución (para preview WebSocket)
3. **Añadir configuración** en `libs/config/settings.py`: `CAMERA_DEVICE_PATH`, `CAMERA_SDK_TYPE` (playerone/v4l2/auto)
4. **Registrar** el driver en `libs/devices/registry.py`
5. **Tests hardware** en `tests/hardware/test_camera_real.py` (skip si no hay cámara)
6. **Documentar** viabilidad del SDK en `docs/risks/hardware-integration.md`

**Archivos clave:**
- `libs/devices/interfaces.py` — CameraDriver abstracta
- `libs/devices/models.py` — CameraConfiguration, CapturedFrame, DeviceStatus
- `libs/devices/stubs.py` — PlayerOneMarsMCameraDriverStub
- `services/simulator/drivers.py` — SimulatedCameraDriver como referencia
- `apps/backend/app/api/routes/devices.py` — endpoints de cámara existentes

**Criterios de aceptación:**
- `connect()` devuelve `DeviceCommandResult(accepted=True)` con cámara real conectada
- `capture_still()` devuelve imagen real (no sintética)
- `configure()` aplica exposure y gain al sensor
- `get_status()` muestra temperatura del sensor real
- Tests hardware pasan con `pytest -m hardware tests/hardware/test_camera_real.py`

---

## SESIÓN 3 — Backend: endpoint park, WebSocket frame streaming y mejoras

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El frontend llama a `POST /api/v1/devices/mount/park` (en `src/api/client.ts`) pero ese endpoint no existe en el backend. También se necesita un WebSocket endpoint que haga streaming de frames de preview de la cámara para la página de Captura.

El WebSocket base existe en `apps/backend/app/api/routes/ws.py` (emite eventos del event bus). El event bus está en `apps/backend/app/core/event_bus.py`.

### Tarea

1. **Añadir endpoint** `POST /devices/mount/park` en `apps/backend/app/api/routes/devices.py`:
   - Park = mover a posición configurable (por defecto AZ=0, ALT=90) o posición home
   - Añadir método `park()` en `MountDriver` interface (opcional, con implementación default que usa `goto`)
   - Añadir en `SimulatedMountDriver`, `AZGo2MountDriverStub` y driver real si existe

2. **Añadir WebSocket endpoint** `GET /api/v1/ws/preview` en nuevo archivo `apps/backend/app/api/routes/ws_preview.py`:
   - Acepta conexión WebSocket
   - Si preview está activo en `DeviceService`, hace polling cada N ms al driver de cámara y envía frames como base64 JPEG
   - Envía `{"type": "frame", "data": "<base64>", "ts": "<iso>"}` o `{"type": "error", "message": "..."}`
   - Parar el streaming cuando el cliente desconecta

3. **Endpoint** `GET /devices/camera/frame` para captura única sin WebSocket (útil para debug)

4. **Corrección** de cualquier discrepancia entre los contratos del `api/client.ts` del frontend y los endpoints reales del backend. Revisar:
   - `api.sessions.end(id)` → en backend es `POST /sessions/{id}/close` (no `/end`)
   - `api.files.list()` → `GET /sessions/files` no existe, debería ser `GET /sessions/{id}/files`

**Archivos clave:**
- `apps/backend/app/api/routes/devices.py`
- `apps/backend/app/api/routes/ws.py`
- `apps/backend/app/api/router.py`
- `apps/frontend/src/api/client.ts`
- `apps/backend/app/core/container.py`

**Criterios de aceptación:**
- `POST /api/v1/devices/mount/park` responde 200 con `{"accepted": true}`
- `WebSocket /api/v1/ws/preview` envía frames si la cámara está en preview
- Inconsistencias entre frontend `client.ts` y backend corregidas

---

## SESIÓN 4 — Frontend: Dashboard completo con datos reales

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`  
**Stack frontend:** React 18 + TypeScript + Vite + Tailwind CSS + Zustand + TanStack Query

### Contexto

El Dashboard básico existe en `apps/frontend/src/pages/Dashboard.tsx`. Muestra estado del sistema, sesión activa y dispositivos. La estructura de la PWA es: `CriticalBar` (barra superior) + `SidePanel` (lateral) + página + `BottomNav` (inferior).

El store global está en `src/store/appStore.ts` (Zustand + persist). El cliente API en `src/api/client.ts`. El tipo `SystemStatus` está en `src/types/contracts.ts`.

El CSS está en `src/index.css` con clases como `.card`, `.btn`, `.badge`, `.device-row`, `.dpad`, `.night-mode`.

### Tarea

Enriquecer el Dashboard (`apps/frontend/src/pages/Dashboard.tsx`) con:

1. **Widget de estado de dispositivos interactivo:**
   - Mostrar montura y cámara con estado visual claro (connected/disconnected/error)
   - Botones inline `Conectar` / `Desconectar` por dispositivo
   - Posición actual AZ/ALT de la montura si está conectada
   - Temperatura del sensor si cámara conectada

2. **Widget de sesión:**
   - Botón para crear sesión en modo `real` (además del existente `simulator`)
   - Mostrar sesión activa con nombre, modo, hora de inicio
   - Botón `Cerrar sesión` si hay sesión activa (llamar `POST /sessions/{id}/close`)

3. **Widget de eventos recientes** mejorado:
   - Mostrar los últimos 5 eventos con tipo, fuente y timestamp formateado
   - Badge de color según tipo (info/warning/error)
   - Actualización vía `useQuery` con `refetchInterval: 3000`

4. **Indicador de conexión al backend:**
   - Si `isError` en query de sistema: mostrar banner "Backend no disponible — modo offline"
   - Botón para reintentar

5. **Modo nocturno:** Respetar `nightMode` del store (ya aplicado en `app-shell` pero asegurar que todos los colores usan las clases CSS correctas)

6. **Hook `useDevices`** en `src/hooks/useDevices.ts`:
   - `useQuery` sobre `api.devices.list()` con `refetchInterval: 5000`
   - Exponer `mountDevice`, `cameraDevice`, `connectDevice`, `disconnectDevice`

**Archivos clave a leer:**
- `apps/frontend/src/pages/Dashboard.tsx` (actual)
- `apps/frontend/src/store/appStore.ts`
- `apps/frontend/src/api/client.ts`
- `apps/frontend/src/index.css`
- `apps/frontend/src/types/` (si existe `contracts.ts`)
- `apps/frontend/src/hooks/useEventStream.ts`

**Criterios de aceptación:**
- Dashboard muestra estado real de dispositivos con botones connect/disconnect funcionales
- El widget de sesión permite crear y cerrar sesiones
- En modo noche (toggle en CriticalBar) todos los colores cambian correctamente
- La página funciona con backend simulador y con backend real

---

## SESIÓN 5 — Frontend: Página Control (montura completa)

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

La página `ControlPage.tsx` existe con un D-pad básico y botones STOP/PARK. Falta: GoTo coordenadas, modo tracking, estado en tiempo real de la montura, paso de slew configurable.

### Tarea

Reescribir/enriquecer `apps/frontend/src/pages/ControlPage.tsx`:

1. **D-pad mejorado:**
   - Velocidades de slew: 1x, 4x, 8x, 16x (pasos: 0.1°, 0.5°, 1°, 2°)
   - Mostrar el paso actual seleccionado
   - Los botones deben responder a `onPointerDown` / `onPointerUp` para slew continuo (enviar comandos repetidos mientras se mantiene pulsado, parar al soltar)

2. **Estado en tiempo real de la montura:**
   - Mostrar AZ actual y ALT actual (de `DeviceStatus.metadata.coordinates`)
   - Actualizar cada 2 segundos con `useQuery` o via WebSocket
   - Indicador visual: IDLE / SLEWING / GOTO / TRACKING

3. **Panel GoTo:**
   - Inputs para AZ (0-360°) y ALT (0-90°)
   - Botón `Ir a` que llama `POST /api/v1/devices/mount/goto`
   - Búsqueda rápida de objeto (input que llama `GET /api/v1/astronomy/catalog/search?q=...`) y botón `Apuntar` que convierte RA/Dec a AZ/ALT (necesita ubicación del observador del store)

4. **Control de tracking:**
   - Selector: OFF / SIDEREAL / SOLAR
   - Llama `POST /api/v1/devices/mount/tracking` con el modo elegido
   - Indicador visual del modo activo

5. **Panel de estado de conexión:**
   - Si montura no conectada: botón `Conectar` prominente
   - Si en error: mensaje descriptivo y botón `Reconectar`

6. **Hook `useMountStatus`** en `src/hooks/useMountStatus.ts`:
   - Polling cada 2s del estado de la montura
   - Exponer `isConnected`, `coordinates`, `trackingMode`, `isMoving`

**Archivos clave:**
- `apps/frontend/src/pages/ControlPage.tsx`
- `apps/frontend/src/api/client.ts`
- `apps/frontend/src/store/appStore.ts` (observer para conversión coords)

---

## SESIÓN 6 — Frontend: Página Captura (cámara + preview)

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

`CapturePage.tsx` existe básicamente vacía o mínima. Necesita: configuración de cámara (exposure, gain, ROI), preview en tiempo real, captura still, histograma básico.

El backend tiene:
- `POST /api/v1/devices/camera/configure` — configura parámetros
- `POST /api/v1/devices/camera/preview/start` y `/stop`
- `POST /api/v1/devices/camera/capture` — captura y guarda imagen
- `WebSocket /api/v1/ws/preview` — streaming de frames (implementado en Sesión 3)

### Tarea

Implementar `apps/frontend/src/pages/CapturePage.tsx`:

1. **Panel de configuración de cámara:**
   - Slider/input para `exposure_ms` (1ms — 60000ms, logarítmico)
   - Slider/input para `gain` (0 — 600)
   - Selector ROI: Full / 1280×960 / 640×480 / 320×240
   - Selector de bin: 1×1 / 2×2 / 4×4
   - Botón `Aplicar` → `POST /api/v1/devices/camera/configure`

2. **Preview en tiempo real:**
   - Conectar a `WebSocket /api/v1/ws/preview`
   - Mostrar frames en un `<canvas>` o `<img>` actualizado continuamente
   - Botones `▶ Iniciar preview` / `⏹ Parar preview`
   - Indicador FPS y tiempo de exposición
   - Si no hay cámara: mostrar placeholder "Cámara no conectada"

3. **Captura still:**
   - Botón `📷 Capturar` → `POST /api/v1/devices/camera/capture`
   - Requiere sesión activa (mostrar aviso si no hay sesión)
   - Mostrar thumbnail de la última captura
   - Mostrar metadatos: timestamp, exposure, gain, nombre de archivo

4. **Modo simple vs avanzado** (del store):
   - Simple: solo exposure básico + botón capturar + preview
   - Avanzado: todos los controles + histograma si es posible

5. **Hook `usePreviewStream`** en `src/hooks/usePreviewStream.ts`:
   - Gestiona conexión WebSocket al preview
   - Exponer `isStreaming`, `lastFrame` (data URL), `fps`, `error`
   - Reconexión automática si se pierde la conexión

**Archivos clave:**
- `apps/frontend/src/pages/CapturePage.tsx`
- `apps/frontend/src/hooks/useEventStream.ts` (referencia para WebSocket)
- `apps/frontend/src/api/client.ts`

---

## SESIÓN 7 — Frontend: Página Plan (catálogo + planner + orbital)

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

`PlanPage.tsx` existe con estructura mínima. El backend tiene:
- `GET /api/v1/astronomy/catalog/search?q=&kinds=&max_results=` — búsqueda de objetos
- `POST /api/v1/astronomy/visibility` — ventana de visibilidad de un objeto
- `POST /api/v1/astronomy/plan` — genera plan de noche
- `GET /api/v1/astronomy/orbital/objects` — lista TLE
- `POST /api/v1/astronomy/orbital/passes` — pases de satélite

El observador (lat/lon/elevation) está en el store Zustand (`observer`).

### Tarea

Implementar `apps/frontend/src/pages/PlanPage.tsx`:

1. **Buscador de objetos del catálogo:**
   - Input de búsqueda con debounce 300ms → llama `api.astronomy.searchCatalog(q)`
   - Filtro por tipo: Messier / NGC / Planeta / Luna / Satélite
   - Lista de resultados: nombre, tipo, magnitud, descripción breve
   - Al seleccionar un objeto: mostrar ventana de visibilidad (llamar `api.astronomy.checkVisibility`)

2. **Detalle de objeto seleccionado:**
   - Nombre, tipo, coordenadas RA/Dec o AZ/ALT
   - Gráfica simple de altitud vs hora (curva de visibilidad) — puede ser texto tabulado si no hay librería de gráficas
   - Mejor ventana de observación hoy
   - Botón `Apuntar` → llama `POST /devices/mount/goto` (si hay sesión activa)
   - Botón `Añadir al plan`

3. **Panel de plan de noche:**
   - Lista de objetos añadidos al plan
   - Botón `Generar plan óptimo` → llama `api.astronomy.generatePlan(targets, observer, nightWindow, mode)`
   - Mostrar el plan generado: lista de observaciones con horario, score, modo recomendado
   - Botón por observación: `Ir ahora`

4. **Panel de satélites (orbital):**
   - Lista de satélites disponibles (`api.astronomy.listTLEObjects()`)
   - Al seleccionar: calcular pases próximos (`api.astronomy.computePasses(name, observer, start, end)`)
   - Mostrar pases: hora de inicio/fin, altitud máxima, dirección
   - Botón `Seguir este pase` (placeholder para futura integración de tracking)

5. **Configuración del observador:**
   - Botón "Mis coordenadas" abre modal con lat/lon/elevation
   - Guarda en el store y persiste

**Archivos clave:**
- `apps/frontend/src/pages/PlanPage.tsx`
- `apps/frontend/src/api/client.ts` (métodos de astronomy)
- `apps/frontend/src/store/appStore.ts` (observer)

---

## SESIÓN 8 — Frontend: Página Archivos + resto de páginas secundarias

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

`FilesPage.tsx` existe con estructura mínima. El backend tiene:
- `GET /api/v1/sessions` — lista sesiones
- `GET /api/v1/sessions/{id}/files` — archivos de una sesión
- `POST /api/v1/sessions/{id}/reconcile` — reconciliar DB/filesystem

Faltan páginas: Dispositivos, Diagnóstico, Ajustes, Ayuda (accedidas desde SidePanel).

### Tarea

1. **`FilesPage.tsx` completa:**
   - Lista de sesiones pasadas (`api.sessions.list()`)
   - Al seleccionar sesión: mostrar sus archivos (`GET /sessions/{id}/files`)
   - Para cada archivo: nombre, tipo, tamaño, timestamp, thumbnail si es imagen
   - Botón `Reconciliar` → `POST /sessions/{id}/reconcile`
   - Descarga de archivo (si el backend expone el path)

2. **Crear `src/pages/DevicesPage.tsx`:**
   - Lista todos los dispositivos con estado detallado
   - Botones connect/disconnect por dispositivo
   - Sección de inyección de fallo (para simulador): selector modo error/disconnect/recover
   - Información técnica de cada driver (nombre, tipo, implementación: simulator/stub/real)

3. **Crear `src/pages/DiagnosticsPage.tsx`:**
   - Estado de salud general del sistema (`GET /api/v1/system/status`)
   - Uptime, versión, entorno
   - Log de eventos recientes
   - Botón `Limpiar caché` (placeholder)

4. **Crear `src/pages/SettingsPage.tsx`:**
   - Modo simple/avanzado toggle
   - Modo nocturno toggle
   - Configuración del observador (lat/lon/elevation/timezone)
   - Tema de color (dark only en V1)
   - Configuración de backend URL (para cuando se cambia la IP de la Raspberry Pi)

5. **Crear `src/pages/SimulatorPage.tsx`:**
   - Panel para inyectar fallos en simulador: `POST /devices/{id}/fault`
   - Modos: error / disconnect / recover
   - Estado actual de faults activos
   - Botón de reset completo

6. **Conectar desde SidePanel:** Asegurarse de que `SidePanel.tsx` navega correctamente a estas páginas y que están incluidas en el router de `App.tsx`

**Archivos clave:**
- `apps/frontend/src/pages/FilesPage.tsx`
- `apps/frontend/src/components/SidePanel.tsx`
- `apps/frontend/src/App.tsx` (añadir nuevas rutas)

---

## SESIÓN 9 — Frontend: Onboarding y flujo de configuración inicial

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

No existe onboarding. La app arranca directamente en el Dashboard. Se necesita un flujo guiado de primer uso (o si no hay sesión/observador configurados).

### Tarea

Crear `src/pages/OnboardingPage.tsx` con un flujo de pasos:

1. **Paso 1 — Bienvenida:**
   - Presentación de Telesco-Pi
   - Selector de modo: `Simulador` (sin hardware) o `Hardware real`
   - Botón `Comenzar`

2. **Paso 2 — Configurar ubicación:**
   - Inputs lat/lon/elevation/timezone
   - Botón `Usar ubicación del navegador` (Geolocation API)
   - Validación básica
   - Guarda en store

3. **Paso 3 — Verificar dispositivos (si modo real):**
   - Muestra estado de montura y cámara
   - Botón `Conectar montura` → `POST /devices/mount.primary/connect`
   - Botón `Conectar cámara` → `POST /devices/camera.primary/connect`
   - Indicadores visuales de estado
   - Si modo simulador: conectar automáticamente los simuladores

4. **Paso 4 — Prueba de cámara (si cámara conectada):**
   - Captura una imagen de prueba
   - Muestra thumbnail
   - Confirmar "Todo OK"

5. **Paso 5 — Crear primera sesión:**
   - Input nombre de sesión
   - Selector modo: real / simulator / hybrid
   - Botón `Crear sesión e ir al Dashboard`

6. **Lógica de activación:**
   - Mostrar onboarding si `localStorage` no tiene `onboarding_completed = true`
   - O si el usuario pulsa "Asistente" en Ajustes
   - Al completar: guardar flag y redirigir a Dashboard

7. **Añadir ruta** `/onboarding` en `App.tsx` y redirección automática si no completado

---

## SESIÓN 10 — Astronomía: Catálogos y motor de visibilidad (implementación completa)

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

Los módulos de astronomía tienen estructura completa en `libs/astronomy/`. Los catálogos están en `libs/astronomy/catalogs/`:
- `loaders.py` — cargadores de catálogo
- `models.py` — modelos de objetos del catálogo
- `search.py` — búsqueda
- `tle_store.py` — almacén de TLE
- `datasets/` — datos crudos

La visibilidad está en `libs/astronomy/visibility/`. Los contratos en `libs/astronomy/contracts/`.

Tests en `tests/unit/astronomy/test_catalogs.py` y `test_visibility.py`.

**Librerías disponibles:** AstroPy, skyfield, astroplan (añadir a `requirements.txt` si no están).

### Tarea

1. **Completar `libs/astronomy/catalogs/`:**
   - `datasets/`: incluir datos Messier (110 objetos), NGC básico (reducido, ~1000 objetos más brillantes), planetas del sistema solar, estrellas brillantes (mag < 3), algunos TLE de ejemplo (ISS, CSS)
   - `loaders.py`: cargar datasets en memoria al arrancar, indexar por ID y por tipo
   - `models.py`: `CatalogObject` con campos: id, name, kind (messier/ngc/planet/star/satellite), ra_deg, dec_deg, magnitude, description, aliases
   - `search.py`: búsqueda por nombre/alias, por tipo, por magnitud máxima, retornar lista paginada

2. **Completar `libs/astronomy/visibility/`:**
   - `engine.py` o módulo equivalente: dado un objeto y un observador (lat/lon/elevation) y una ventana temporal, calcular:
     - altitud máxima durante la ventana
     - instante de altitud máxima
     - ventana de visibilidad sobre `min_altitude` configurable (por defecto 20°)
     - score de visibilidad (0-100, basado en altitud, magnitud, tipo)
   - Usar `astropy.coordinates` o `skyfield` para cálculos precisos
   - Para planetas: usar efemérides de AstroPy (builtin, no descargar)
   - Para satélites: delegar a módulo orbital

3. **Completar `libs/astronomy/contracts/visibility.py`** con modelos Pydantic:
   - `VisibilityWindow`: target_id, max_altitude_deg, best_time_utc, visible_from_utc, visible_to_utc, score, score_explanation

4. **Conectar con el backend** en `apps/backend/app/core/container.py` (clase `AstronomyService`): asegurar que `search_catalog` y `compute_visibility` llaman correctamente a los módulos implementados

5. **Tests** en `tests/unit/astronomy/test_catalogs.py` y `test_visibility.py`:
   - Verificar que Messier 31 (M31, Andrómeda) aparece en búsqueda
   - Verificar que la Luna tiene visibilidad calculable
   - Verificar que Saturno tiene score > 0 si está por encima del horizonte

**Archivos clave:**
- `libs/astronomy/catalogs/` (todos los archivos)
- `libs/astronomy/visibility/`
- `libs/astronomy/contracts/visibility.py` y `catalogs.py`
- `apps/backend/app/core/container.py` (AstronomyService)
- `tests/unit/astronomy/test_catalogs.py`, `test_visibility.py`

---

## SESIÓN 11 — Astronomía: Planner/scheduler de noche (implementación completa)

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El planner está en `libs/astronomy/planner/`:
- `scheduler.py` — lógica de scheduling
- `models.py` — modelos
- `rules.py` — reglas de planificación
- `explanations.py` — explicabilidad

Contratos en `libs/astronomy/contracts/planning.py`.

Tests en `tests/unit/astronomy/test_planner.py`.

### Tarea

1. **Completar `libs/astronomy/planner/scheduler.py`:**
   - Input: lista de target_ids, observador, ventana nocturna (start/end UTC), modo (planetary/eaa/orbital/mixed), constraints opcionales
   - Para cada target: calcular ventana de visibilidad (usar módulo visibility), calcular score
   - Ordenar por score, resolver conflictos de tiempo, asignar franjas horarias
   - Output: `NightPlan` con lista de `PlannedObservation` (target, start, end, score, mode, explanation, warnings)

2. **Reglas de planificación** (`rules.py`):
   - No observar objetos con ALT < min_altitude (20° por defecto)
   - No observar con Sol sobre horizonte (calcular amanecer/atardecer)
   - Priorizar objetos near meridian (mayor altitud)
   - Para EAA/DSO: evitar luna llena > 50% iluminación si separación < 30°
   - Para planetaria: priorizar cuando planeta está cerca del meridiano

3. **Explicabilidad** (`explanations.py`):
   - Cada observación incluye `reasoning` en texto legible: "M31 seleccionado a las 22:30 (altitud máxima 68°, luna separada 95°, score=87)"

4. **Contratos** (`libs/astronomy/contracts/planning.py`):
   - `PlannerRequest`, `PlannedObservation`, `NightPlan` con modelos Pydantic completos

5. **Tests** en `tests/unit/astronomy/test_planner.py`:
   - Plan vacío para ventana corta sin objetos visibles → debe retornar plan vacío con explicación
   - Plan con M31 y Júpiter desde Madrid en agosto → debe incluir ambos si visibles
   - Verificar que explicaciones están presentes

---

## SESIÓN 12 — Astronomía: Plate solving con astrometry.net local

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El módulo de plate solving está en `libs/astronomy/solving/`:
- `astrometry_net.py` — integración con astrometry.net local
- `preprocess.py` — preprocesado de imagen para solve
- `confidence.py` — métricas de confianza del solve
- `fallback.py` — fallback opcional

Contratos en `libs/astronomy/contracts/solving.py`.

**Nota:** `astrometry.net` local requiere instalación del paquete `astrometry` y descarga de índices. En Raspberry Pi 5 con almacenamiento limitado se recomienda los índices 4100-4119 (estrellas brillantes, suficientes para campo Newton 130/650).

### Tarea

1. **`libs/astronomy/solving/preprocess.py`:**
   - Dado un `CapturedFrame` (bytes PGM, FITS, o RAW), convertir a formato aceptado por astrometry.net
   - Usar `OpenCV` o `PIL` para preprocesar: resize si es muy grande, stretch básico para detectar estrellas
   - Retornar path temporal de archivo de imagen preprocesada

2. **`libs/astronomy/solving/astrometry_net.py`:**
   - Detectar si `solve-field` está instalado (`shutil.which('solve-field')`)
   - Si no está: devolver `SolveResult(success=False, reason="astrometry.net not installed")`
   - Si está: ejecutar `solve-field` con parámetros apropiados para Newton 130/650 (FOV ~2.3° × 1.7°)
   - Parsear output: extraer RA/Dec center, pixel scale, rotation
   - Timeout configurable (30s por defecto)
   - Limpiar archivos temporales

3. **`libs/astronomy/solving/confidence.py`:**
   - Métricas del solve: número de estrellas detectadas, RMS de residuales, índice usado
   - Score de confianza 0-1

4. **Integración con pointing model** (`libs/astronomy/pointing/`):
   - Si solve exitoso: actualizar referencia de pointing en `PointingModel`
   - Exponer `calibrate_from_solve(solve_result, mount_coordinates)` en el modelo de apuntado

5. **Endpoint en backend** `POST /api/v1/astronomy/solve` en `apps/backend/app/api/routes/contracts.py`:
   - Recibe `session_id` y `file_id` (de una captura existente)
   - Ejecuta solve sobre ese archivo
   - Retorna `SolveResult`

6. **Tests** en `tests/unit/astronomy/` — test con imagen sintética que tenga estrellas conocidas

---

## SESIÓN 13 — Astronomía: Calibración y pointing model

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El módulo de calibración está en `libs/astronomy/calibration/`:
- `alignment.py` — alineado inicial
- `confidence.py` — confianza del modelo
- `persistence.py` — guardado del modelo
- `reference_state.py` — estado de referencia

El pointing model está en `libs/astronomy/pointing/`.

Contratos en `libs/astronomy/contracts/calibration.py`.

### Tarea

1. **`libs/astronomy/pointing/` — PointingModel:**
   - Almacena lista de `PointingReference(mount_az, mount_alt, sky_ra, sky_dec, timestamp, confidence)`
   - Con 1 referencia: corrección de offset simple (az_offset, alt_offset)
   - Con 2+ referencias: modelo de transformación afín 2D (usar numpy.linalg para ajuste de mínimos cuadrados)
   - Método `predict_sky(mount_az, mount_alt)` → RA/Dec predichos
   - Método `correct_mount(ra, dec)` → AZ/ALT corregidos para GoTo
   - Método `confidence_score()` → 0-1 basado en número de referencias y residuales

2. **`libs/astronomy/calibration/alignment.py`:**
   - Flujo de calibración de 1 estrella: usuario apunta a estrella conocida, captura imagen, plate solve, registrar referencia
   - Flujo de 2-3 estrellas: ídem, mejora el modelo
   - `CalibrationSession` con estado: NOT_STARTED / IN_PROGRESS / COMPLETED / FAILED

3. **`libs/astronomy/calibration/persistence.py`:**
   - Guardar/cargar PointingModel en JSON en la sesión activa
   - Path: `<storage_path>/sessions/<session_id>/pointing_model.json`

4. **Endpoint en backend** `POST /api/v1/astronomy/calibration/reference` y `GET /api/v1/astronomy/calibration/model`:
   - Añadir referencia de calibración (mount coords + solve result)
   - Obtener modelo actual y su confianza

5. **Tests** en `tests/unit/astronomy/test_pointing.py`:
   - Con 1 referencia: corrección de offset simple verificable
   - Con 3 referencias: verificar que `predict_sky` da RA/Dec razonables

---

## SESIÓN 14 — Astronomía: Pipeline planetario/lunar avanzado

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El pipeline planetario está en `libs/astronomy/processing/planetary/pipeline.py` (estructura existe, implementación parcial).

El framework de pipelines está en `libs/astronomy/processing/framework/`.

La métrica de calidad de frames está en `libs/astronomy/processing/quality/`.

Jobs en `libs/astronomy/jobs/`.

Contratos en `libs/astronomy/contracts/planetary.py`.

**Hardware disponible para pruebas:** Cámara Player One Mars M conectada. Se pueden capturar imágenes reales de planetas/luna para validar.

### Tarea

1. **Framework de pipelines** (`libs/astronomy/processing/framework/`):
   - Clase `Pipeline` con: id, name, type, version, steps, parameters, estimated_cost
   - Clase `PipelineStep` con: name, function, parameters
   - Ejecución secuencial de pasos con logging y timing por paso
   - Estado del pipeline: PENDING / RUNNING / COMPLETED / FAILED
   - Resultado serializable con metadata

2. **Métricas de calidad de frame** (`libs/astronomy/processing/quality/`):
   - `frame_quality_score(image_array)` → score 0-1 + métricas: sharpness (Laplacian variance), contrast, SNR estimado
   - Implementar con `OpenCV` (cv2.Laplacian, cv2.calcHist)

3. **Pipeline planetario** (`libs/astronomy/processing/planetary/pipeline.py`):
   - Step 1: Cargar frames de una secuencia (lista de paths o bytes)
   - Step 2: Calcular calidad de cada frame (lucky imaging)
   - Step 3: Seleccionar top-N% de frames por calidad (configurable: 10%, 25%, 50%)
   - Step 4: Detectar y centrar el disco planetario (usar OpenCV: encontrar blob circular más brillante)
   - Step 5: Alineación sub-pixel entre frames seleccionados (cross-correlation con scipy o OpenCV)
   - Step 6: Stacking (media, mediana, o sigma-clipping — implementar los 3)
   - Step 7: Sharpening (unsharp mask básico con cv2.GaussianBlur + factor)
   - Step 8: Stretch y export (guardar como PNG/TIFF con metadatos)
   - Niveles: LOW (25% frames, media, no sharpen) / BALANCED / HIGH (10%, sigma-clip, sharpen)

4. **Jobs** (`libs/astronomy/jobs/orchestration.py`):
   - `PlanetaryPipelineJob` que ejecuta el pipeline en proceso separado (asyncio.to_thread o ProcessPoolExecutor)
   - Estado observable: `GET /api/v1/astronomy/jobs/{job_id}`

5. **Tests** en `tests/unit/astronomy/test_processing.py`:
   - Con stack de imágenes sintéticas (ruido gaussiano + disco circular): verificar que el stacking reduce ruido

---

## SESIÓN 15 — Astronomía: Live stacking / EAA

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El módulo de live stacking está en `libs/astronomy/processing/livestack/engine.py`.

Tests en `tests/unit/astronomy/test_livestack.py`.

Contratos en `libs/astronomy/contracts/livestack.py`.

**Hardware disponible:** Cámara conectada. Se pueden capturar frames reales para EAA.

### Tarea

1. **`libs/astronomy/processing/livestack/engine.py` — LiveStackEngine:**
   - Estado: `IDLE / RUNNING / PAUSED / COMPLETED`
   - `start_session(config)`: inicializa acumulador, configura parámetros
   - `add_frame(image_bytes, metadata)`: procesa un nuevo frame:
     - Convertir a numpy array
     - Calcular calidad → si < threshold: rechazar (loggear)
     - Detectar estrellas (usar `photutils.detection.DAOStarFinder` o `OpenCV GoodFeaturesToTrack`)
     - Alinear con el frame de referencia (affine transform, usar cv2.estimateAffinePartial2D)
     - Acumular en buffer (suma running o media)
   - `get_preview()`: retornar imagen actual acumulada con auto-stretch (percentile stretch)
   - `save_result(path)`: guardar stack final como FITS o TIFF
   - `reset()`: reiniciar acumulador manteniendo configuración
   - Límite de memoria: acumulador de float32, máximo configurable (por defecto 500 frames × resolución)

2. **Auto-stretch** para preview:
   - Stretch de percentil: escalar entre percentil 5 y 99.9
   - Retornar como JPEG bytes para enviar via WebSocket

3. **Endpoint en backend** `POST /api/v1/astronomy/livestack/start`, `/add_frame`, `/preview`, `/stop`:
   - O integrar con WebSocket para streaming del preview acumulado
   - La cámara en modo preview puede alimentar el live stack

4. **Contratos** `libs/astronomy/contracts/livestack.py`:
   - `LiveStackConfig`, `LiveStackStatus`, `FrameResult` (accepted/rejected + reason)

5. **Tests** en `tests/unit/astronomy/test_livestack.py`:
   - Stack de 10 imágenes sintéticas con estrellas → verificar mejora de SNR vs frame único
   - Verificar rechazo de frames con calidad < threshold

---

## SESIÓN 16 — Astronomía: Orbital tracking completo

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El módulo orbital está en `libs/astronomy/orbital/`:
- `tle.py` — parsing y gestión de TLE
- `propagation.py` — propagación orbital
- `passes.py` — cálculo de pases
- `tracking.py` — tracking en tiempo real
- `recommendations.py` — recomendaciones para captura

Contratos en `libs/astronomy/contracts/orbital.py`.

Tests en `tests/unit/astronomy/test_orbital.py`.

**Librerías:** `sgp4`, `skyfield` (añadir a requirements.txt si faltan).

### Tarea

1. **`libs/astronomy/orbital/tle.py`:**
   - Parser de TLE format (2 líneas)
   - `TLERecord(name, line1, line2, epoch, source, updated_at)`
   - Cargar TLE de archivo local (datasets/tle_sample.txt con ISS, CSS, varios LEO)
   - `TLEStore`: almacenar en memoria/SQLite, actualizar desde URL (opcional, marcado como secundario)

2. **`libs/astronomy/orbital/propagation.py`:**
   - Usar `sgp4` para propagar posición orbital
   - `propagate(tle_record, timestamp_utc)` → (x, y, z) en ECI
   - Convertir ECI → AZ/ALT para un observador dado (usar astropy o calcular manualmente)
   - Verificar validez temporal del TLE (advertir si > 7 días de antigüedad)

3. **`libs/astronomy/orbital/passes.py`:**
   - `compute_passes(tle_record, observer, start_utc, end_utc, min_alt_deg=10)` → lista de `OrbitalPass`
   - `OrbitalPass(aos_utc, los_utc, max_alt_deg, max_alt_az_deg, duration_seconds, trajectory_az_alt_pairs)`
   - Algoritmo: evaluar posición cada 10s, detectar cruce de horizonte, refinar con bisección

4. **`libs/astronomy/orbital/tracking.py`:**
   - `TrackingPlan(tle_record, observer, start_utc)` → secuencia de comandos AZ/ALT para la montura cada T segundos
   - `generate_tracking_sequence(tle, observer, pass_event, interval_seconds=1)` → lista de `(timestamp, az_deg, alt_deg)`
   - Contratos para integración con mount driver (lista de comandos goto timed)

5. **Tests** en `tests/unit/astronomy/test_orbital.py`:
   - Parse TLE de ISS y propagar posición en tiempo conocido
   - Calcular pases para Madrid y verificar que hay al menos 1 en 24h
   - Generar secuencia de tracking y verificar formato

---

## SESIÓN 17 — Backend: Integración completa de astronomy service y jobs

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El `AstronomyService` en `apps/backend/app/core/container.py` conecta el backend con los módulos de astronomía. Los jobs están en `libs/astronomy/jobs/`. Los endpoints de astronomía están en `apps/backend/app/api/routes/contracts.py`.

### Tarea

1. **Completar `AstronomyService`** en `apps/backend/app/core/container.py`:
   - Asegurar que todos los métodos llaman correctamente a los módulos de astronomía implementados en sesiones 10-16
   - `search_catalog()` → catalogs.search
   - `compute_visibility()` → visibility engine
   - `generate_plan()` → planner scheduler
   - `compute_passes()` → orbital passes
   - `list_tle_objects()` → tle store

2. **Sistema de jobs** (`libs/astronomy/jobs/`):
   - `JobRegistry`: almacena jobs activos y completados en memoria
   - `JobStatus`: PENDING / RUNNING / COMPLETED / FAILED / CANCELLED
   - `Job`: id, type, status, created_at, started_at, completed_at, result, error
   - Jobs largos (plate solving, pipeline planetario, live stacking) se ejecutan en `asyncio.to_thread`

3. **Endpoints de jobs** en el backend:
   - `GET /api/v1/jobs` — listar jobs activos y recientes
   - `GET /api/v1/jobs/{job_id}` — estado de un job
   - `DELETE /api/v1/jobs/{job_id}` — cancelar job

4. **Endpoint de solve** `POST /api/v1/astronomy/solve`:
   - Recibe `{session_id, file_id}`
   - Crea job de plate solving
   - Retorna `{job_id, status: "pending"}`

5. **Endpoint de pipeline** `POST /api/v1/astronomy/pipeline/planetary`:
   - Recibe `{session_id, frame_ids, config}`
   - Crea job de pipeline planetario
   - Retorna `{job_id}`

6. **WebSocket mejora** — emitir `job.updated` events cuando cambia estado de un job

---

## SESIÓN 18 — Infraestructura: Scripts de despliegue en Raspberry Pi 5

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

`infra/scripts/` está vacío. `infra/systemd/` probablemente también. El backend se ejecuta con `uvicorn` y el frontend se sirve como archivos estáticos.

### Tarea

1. **`infra/scripts/bootstrap.sh`** — script de instalación inicial en Raspberry Pi OS 64-bit (Ubuntu 22.04 o Bookworm):
   ```bash
   # Debe hacer:
   # 1. Actualizar sistema (apt update/upgrade)
   # 2. Instalar Python 3.11, pip, venv
   # 3. Instalar Node.js 20 LTS (via nvm o nodesource)
   # 4. Instalar dependencias del sistema: libopencv-dev, libusb-1.0-0-dev, etc.
   # 5. Clonar/actualizar repositorio
   # 6. Crear virtualenv Python e instalar requirements.txt
   # 7. Build del frontend (npm install + npm run build)
   # 8. Crear directorios de datos: /opt/telesco-pi/{data,captures,logs}
   # 9. Instalar servicios systemd
   # 10. Habilitar y arrancar servicios
   ```

2. **`infra/scripts/deploy.sh`** — actualización de una instalación existente:
   - Pull de repositorio
   - Reinstalar requirements si cambiaron
   - Rebuild frontend
   - Reiniciar servicio

3. **`infra/systemd/telesco-pi-backend.service`:**
   ```ini
   [Unit]
   Description=Telesco-Pi Backend API
   After=network.target
   
   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/opt/telesco-pi
   Environment=ENVIRONMENT=production
   Environment=DEVICE_MODE=real
   ExecStart=/opt/telesco-pi/venv/bin/uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000
   Restart=on-failure
   RestartSec=5
   
   [Install]
   WantedBy=multi-user.target
   ```

4. **`infra/configs/production.env`** — plantilla de variables de entorno para producción:
   - ENVIRONMENT, DEVICE_MODE, MOUNT_HOST, MOUNT_PORT, CAMERA_SDK_TYPE, STORAGE_PATH, LOG_LEVEL, CORS_ORIGINS

5. **`infra/scripts/check_hardware.sh`** — script de diagnóstico de hardware:
   - Verificar que AZ-Go2 es alcanzable (ping/telnet al puerto 11882)
   - Verificar que la cámara aparece en `lsusb`
   - Verificar espacio en disco
   - Mostrar temperatura del CPU

6. **`docs/deployment/raspberry-setup.md`** — guía paso a paso de instalación

---

## SESIÓN 19 — Tests de integración de hardware: Montura

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`  
**Hardware disponible:** Montura SkyWatcher AZ-Go2 WiFi conectada

### Contexto

`tests/hardware/` está vacío. Los tests de hardware deben marcarse con `@pytest.mark.hardware` y pueden skipearse en CI. Configurar en `pyproject.toml` o `pytest.ini` para que `pytest -m hardware` los ejecute y `pytest` normal los salte.

### Tarea

Crear `tests/hardware/test_mount_real.py` con los siguientes tests (todos marcados `@pytest.mark.hardware`):

1. **test_mount_connection()**: Conectar al driver real. Verificar `DeviceConnectionState.CONNECTED`.
2. **test_mount_get_status()**: Verificar que el status retorna coordenadas AZ/ALT válidas (no None, AZ en [0,360], ALT en [-10,90]).
3. **test_mount_manual_slew_small()**: Slew de +0.2° en AZ. Leer posición antes y después. Verificar cambio ≈ 0.2° (tolerancia ±0.5°).
4. **test_mount_stop()**: Iniciar slew, llamar stop(), verificar que se detiene.
5. **test_mount_tracking_off()**: Poner tracking en OFF. Verificar `DeviceCommandResult(accepted=True)`.
6. **test_mount_tracking_sidereal()**: Poner tracking en SIDEREAL. Verificar aceptado.
7. **test_mount_goto_current_plus_delta()**: Leer posición actual, hacer goto a posición actual + (2°, 0°). Verificar que llega (tolerancia ±1°).
8. **test_mount_park()**: Ejecutar park. Verificar posición parkeo (AZ≈0, ALT≈90 o la configurada).
9. **test_mount_disconnect()**: Desconectar. Verificar `DeviceConnectionState.DISCONNECTED`.

También crear `conftest.py` en `tests/hardware/` con:
- Fixture `mount_driver` que crea y conecta el driver real, y hace teardown (disconnect) al finalizar
- Skip automático si `MOUNT_HOST` no está configurado o no es alcanzable

---

## SESIÓN 20 — Tests de integración de hardware: Cámara

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`  
**Hardware disponible:** Cámara Player One Mars M USB 3.0 conectada

### Contexto

Igual que la sesión anterior pero para la cámara. Tests en `tests/hardware/test_camera_real.py`.

### Tarea

Crear `tests/hardware/test_camera_real.py`:

1. **test_camera_connection()**: Conectar al driver real. Verificar `CONNECTED`.
2. **test_camera_get_status()**: Verificar temperatura del sensor (valor razonable, por ejemplo -40 a +80°C).
3. **test_camera_configure_basic()**: Configurar exposure=100ms, gain=100, ROI=640×480. Verificar `accepted=True`.
4. **test_camera_capture_still_returns_image()**: Capturar still. Verificar:
   - `CapturedFrame` con `bytes_payload` no vacío
   - `width` y `height` correctos según ROI configurado
   - Bytes parseables como imagen
5. **test_camera_preview_start_stop()**: Iniciar preview, esperar 2s, parar. Verificar sin errores.
6. **test_camera_capture_high_gain()**: gain=400, exposure=10ms. Capturar y verificar.
7. **test_camera_capture_sequence()**: Capturar 5 frames consecutivos. Verificar que son diferentes (suma de bytes distinta).
8. **test_camera_roi_full()**: Configurar ROI full resolution. Capturar y verificar dimensiones.
9. **test_camera_disconnect()**: Desconectar. Verificar `DISCONNECTED`.

Fixture `camera_driver` con connect/disconnect automático.

---

## SESIÓN 21 — Tests end-to-end de la API backend

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

Los tests de integración de API están en `tests/integration/`. Usar `httpx.AsyncClient` con la app FastAPI en modo test (simulador).

### Tarea

Crear/completar `tests/integration/test_api_full.py` con tests completos del API usando simulador:

1. **Health y sistema:**
   - `GET /api/v1/health/live` → 200, `{status: "ok"}`
   - `GET /api/v1/system/status` → 200, incluye devices y events

2. **Ciclo de sesión:**
   - Crear sesión → `{session.id}` retornado
   - Listar sesiones → incluye la creada
   - Obtener sesión activa
   - Cerrar sesión
   - Verificar sesión cerrada en lista

3. **Ciclo de dispositivos (simulador):**
   - Listar dispositivos → 2 (mount.primary, camera.primary)
   - Conectar montura → accepted
   - Conectar cámara → accepted
   - Status montura → CONNECTED
   - Manual slew +1° → accepted
   - Stop → accepted
   - Tracking sidereal → accepted
   - Configurar cámara → accepted
   - Start preview → accepted
   - Stop preview → accepted
   - Capture still (con sesión activa) → retorna file + preview
   - Park → accepted
   - Desconectar → accepted

4. **Inyección de fallo y recuperación:**
   - Conectar montura simulada
   - Inyectar fallo `disconnect`
   - Intentar slew → debe fallar con error coherente
   - Inyectar recover → accepted
   - Slew de nuevo → funciona

5. **Astronomy:**
   - Buscar "M31" en catálogo → aparece Andrómeda
   - Buscar "ISS" → aparece en TLE objects
   - Compute passes ISS → lista de pases

6. **Reconciliación:**
   - Crear sesión, capturar imagen, reconciliar → report sin errores

---

## SESIÓN 22 — Mejoras de UX nocturna y accesibilidad del frontend

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El CSS base está en `apps/frontend/src/index.css`. Existe `.night-mode` aplicado al `app-shell`. Los componentes `CriticalBar.tsx`, `BottomNav.tsx`, `SidePanel.tsx` existen.

### Tarea

1. **Sistema de diseño dark-first mejorado** en `src/index.css`:
   - Variables CSS: `--color-bg-primary: #0d0d0d`, `--color-bg-surface: #1a1a1a`, `--color-text-primary: #e8e8e8`, `--color-accent: #4a9eff`, `--color-warning: #ffb347`, `--color-danger: #ff4444`, `--color-success: #44ff88`
   - Modo nocturno rojo: `--color-night-red: #cc2200`, override todas las luces azules por rojos oscuros
   - Transición suave: `transition: background-color 0.3s, color 0.3s`

2. **`CriticalBar.tsx` mejorada:**
   - Siempre visible en top: STOP, PARK, CAPTURAR, MODO NOCHE toggle
   - Indicador de conexión (punto verde/rojo)
   - Indicador de sesión activa
   - Notificaciones con badge de cuenta

3. **`BottomNav.tsx` mejorada:**
   - Íconos más grandes (min 48×48px touch target)
   - Indicador de página activa (resaltado, no solo subrayado)
   - Badge en "Archivos" si hay capturas nuevas

4. **Confirmación en acciones peligrosas:**
   - STOP: inmediato (sin confirmación)
   - PARK: confirmación rápida modal "¿Aparcar montura?"
   - Cerrar sesión: confirmación "¿Cerrar sesión con N capturas?"

5. **Estados de carga y error uniformes:**
   - Componente `<LoadingSpinner />` reutilizable
   - Componente `<ErrorBanner message={...} onRetry={...} />` reutilizable
   - Componente `<EmptyState icon={...} message={...} />` reutilizable
   - Usar en todas las páginas existentes

6. **Responsive para tablet/portátil:**
   - En pantalla ≥ 768px: SidePanel siempre visible (no drawer)
   - BottomNav se convierte en nav lateral en ≥ 768px
   - Grid de 2 columnas para cards en pantallas grandes

---

## SESIÓN 23 — Notificaciones y center de eventos en tiempo real

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

El WebSocket de eventos existe (`/api/v1/ws`). El hook `useEventStream.ts` existe. El store tiene `unreadNotifications`. Falta un centro de notificaciones visible.

### Tarea

1. **`src/components/NotificationCenter.tsx`:**
   - Panel deslizable desde la barra superior
   - Lista de notificaciones con: tipo (info/warning/error/event), mensaje, timestamp, fuente
   - Badge de no leídas en CriticalBar
   - Marcar todas como leídas
   - Tipos de notificaciones: `device.connected`, `device.disconnected`, `device.error`, `session.created`, `session.closed`, `capture.completed`, `job.completed`, `job.failed`

2. **`src/hooks/useEventStream.ts` mejorado:**
   - Reconexión automática con exponential backoff (1s, 2s, 4s, 8s, máx 30s)
   - Indicador de estado de conexión en el store: `wsConnected: boolean`
   - Cuando llega evento: añadir a lista de notificaciones en store

3. **`src/store/notificationStore.ts`** (nuevo store):
   - `notifications: Notification[]` (máx 50, FIFO)
   - `addNotification(event)`, `markAllRead()`, `clearAll()`
   - Persistencia de las últimas notificaciones

4. **Toast de eventos críticos:**
   - Si llega `device.error` o `job.failed`: mostrar toast visible 5s
   - Componente `<Toast />` con animación y auto-dismiss

---

## SESIÓN 24 — PWA: Service Worker y capacidades offline

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

`vite.config.ts` existe. El frontend es una Vite app. Para PWA se puede usar el plugin `vite-plugin-pwa` (aún no instalado).

### Tarea

1. **Instalar y configurar** `vite-plugin-pwa`:
   ```bash
   cd apps/frontend && npm install -D vite-plugin-pwa
   ```

2. **Configurar** `vite.config.ts` con `VitePWA`:
   - `registerType: 'autoUpdate'`
   - `manifest`: name, short_name, icons (192×192, 512×512 — crear SVG a PNG básico), theme_color, background_color, display: 'standalone'
   - Cache strategy: `StaleWhileRevalidate` para assets, `NetworkFirst` para API calls, `CacheFirst` para imágenes capturadas

3. **`public/manifest.json`** con metadatos de la PWA:
   - nombre, iconos, orientación preferida (portrait)

4. **Comportamiento offline:**
   - Shell de la app (HTML, CSS, JS) siempre en caché
   - Cuando API no disponible: mostrar datos cacheados de última visita + banner offline
   - No bloquear navegación si backend está offline

5. **Actualización de versión:**
   - Cuando hay nueva versión del SW: mostrar toast "Nueva versión disponible — actualizar"
   - Botón "Actualizar ahora" que recarga la app

6. **`public/` folder:**
   - Crear iconos básicos `icon-192.png` e `icon-512.png` (pueden ser simples con telescopio emoji sobre fondo oscuro)

---

## SESIÓN 25 — Revisión final, tests de smoke y documentación

**Repositorio:** `dot-gabriel-ferrer/telesco-pi`

### Contexto

Tras todas las sesiones anteriores, esta sesión hace una revisión integral y cierra la documentación.

### Tarea

1. **Smoke tests de API** — Ejecutar contra backend local con simulador:
   ```bash
   cd apps/backend
   python -m pytest tests/integration/ -v --tb=short
   ```
   Corregir cualquier fallo.

2. **Tests unitarios de astronomía** — Ejecutar:
   ```bash
   python -m pytest tests/unit/ -v --tb=short
   ```
   Corregir cualquier fallo.

3. **Build del frontend** — Verificar que compila sin errores:
   ```bash
   cd apps/frontend && npm run build
   ```
   Corregir errores de TypeScript si los hay.

4. **Documentación faltante** — Revisar y crear/actualizar:
   - `docs/architecture/backend.md` — arquitectura del backend con diagrama Mermaid
   - `docs/architecture/device-abstractions.md` — interfaces de drivers y diagrama de herencia
   - `docs/api/contracts.md` — lista de todos los endpoints con request/response
   - `docs/deployment/raspberry-setup.md` — guía completa de instalación
   - `docs/testing/hardware-tests.md` — instrucciones para ejecutar tests de hardware
   - `docs/risks/hardware-integration.md` — estado de integración real vs stub

5. **`README.md`** — Actualizar sección "Inicio rápido" con instrucciones reales:
   ```bash
   # Backend
   pip install -r apps/backend/requirements.txt
   uvicorn apps.backend.app.main:app --reload
   
   # Frontend
   cd apps/frontend && npm install && npm run dev
   
   # Tests simulador
   pytest tests/unit/ tests/integration/
   
   # Tests hardware (requiere hardware conectado)
   pytest -m hardware tests/hardware/
   ```

6. **Checklist de estado del proyecto:**
   - Crear `docs/status.md` con tabla de módulos: implementado / parcial / pendiente / stub

---

## Notas generales para todos los prompts

- **Hardware siempre disponible**: La montura SkyWatcher AZ-Go2 WiFi y la cámara Player One Mars M están conectadas. Usa hardware real cuando el prompt lo indique.
- **Simulador siempre funcional**: No romper `SimulatedMountDriver` ni `SimulatedCameraDriver` en ninguna sesión.
- **Tests**: Añadir tests para todo lo implementado. Marcar tests de hardware con `@pytest.mark.hardware`.
- **No romper lo existente**: Antes de hacer cambios, ejecutar `pytest tests/unit/ tests/integration/` para verificar estado base.
- **Contexto del repositorio**: El repositorio completo está en `dot-gabriel-ferrer/telesco-pi`. Siempre leer los archivos clave mencionados en cada prompt antes de implementar.
- **Formato de salida**: Código organizado por archivo con rutas explícitas. No mezclar pseudocódigo con código real.
- **Modo de trabajo**: Leer → planificar → implementar → testear. No saltar pasos.
