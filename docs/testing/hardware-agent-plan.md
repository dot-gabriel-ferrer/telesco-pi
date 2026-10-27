# Plan de banco para un agente de IA

**Estado:** preparado para ejecución supervisada; ninguna prueba física aprobada.
Destino inicial: **este ordenador Linux x64**; despliegue posterior en
Raspberry Pi 5/Linux ARM64 con la misma distribución. Cámara Player One
Mars-M monocroma o Mars-C color, y SkyWatcher AZ-Go2 WiFi. El agente es
[Telesco-Pi Hardware Validation](../../.github/agents/hardware-validation.agent.md).
No es un procedimiento de observación solar ni de movimiento autónomo.

## 1. Contrato de ejecución

El operador proporciona **antes de H1**: identidad del Linux local, o host/IP
y acceso SSH ya autorizado si el equipo es remoto; ruta del repositorio,
modelo de ordenador/OS, modelo y serial de cámara,
firmware de montura, interfaz/red de control, operador presencial y carpeta
nueva de evidencias. No incluir contraseñas, tokens ni claves en los informes.
Si falta un dato, preguntar; no descubrir equipos ajenos ni inventarlo.

Invocar manualmente al agente desde VS Code con, por ejemplo:

Abrir primero la raíz de `telesco-pi` como proyecto para que VS Code detecte
`.github/agents/`; seleccionar **Telesco-Pi Hardware Validation**.

> Ejecuta H0 y prepara H1 del plan hardware. El equipo es LOCAL/HOST, el repositorio está
> en RUTA y el run_id es FECHA-UTC-ID. No autorizo aún exposiciones ni motores.
> Registra los bloqueos y espera mi aprobación para la siguiente puerta.

Las rutas/datos en mayúsculas son marcadores, **no comandos listos para pegar**.
Los comandos siguientes se ejecutan desde la raíz del repositorio de destino
con su `.venv`, salvo indicación. H0 se puede ejecutar en desarrollo.

### Autorizaciones independientes, actuales y acotadas

| Puerta | Autoriza | No autoriza |
| --- | --- | --- |
| G0 | H0, lecturas de sistema y enumeración sin apertura | Instalar servicios, cambiar red/permisos, abrir cámara |
| G1 | Instalar dependencias o permisos concretos revisados | Ejecutar como root el backend, usar muestras del SDK |
| G2 | Abrir cámara y realizar exposiciones, número/duración definidos | ST4, motores, tocar cableado sin operador |
| G3 | Handshake de montura y STOP de ambos ejes al cerrar | Movimiento, seguimiento, GoTo o PARK |
| G4 | Un caso de movimiento: eje, signo, grados, velocidad y recorrido total | Repetición automática, cambio de eje o recuperación autónoma |
| G5 | Una intervención concreta: USB, red o reinicio limpio | Cortar alimentación escribiendo ni fallos con motores activos |

Registrar quién, UTC, mensaje de aprobación, alcance y vencimiento en el
informe. Un archivo con `approved=true` no constituye permiso; tampoco el modo
autopilot. Las puertas caducan al reiniciar, cambiar configuración/equipo,
ausentarse el operador o iniciar otra ejecución. Después de FAIL, no avanzar.

## 2. Preparación y trazabilidad

Crear una carpeta **nueva**, fuera del control de versiones, por ejecución:

```text
.runtime-data/hardware/RUN_ID/
  report.json
  report.md
  identity/       # HEAD, diff hash, OS, arquitectura, seriales locales, SDK
  commands/       # comando, UTC, código de salida, stdout y stderr
  camera/         # originales PNG16, preview, camera-bench.json
  api/            # respuestas JSON, tiempos, hashes de descargas
  mount/          # handshake, STOP, aprobaciones y observación del operador
  metrics/        # temperatura, throttling, RSS, disco y conectividad
  ui/             # capturas y observaciones del móvil
```

Guardar `git rev-parse HEAD`, `git status --short` y SHA256 de `git diff HEAD
--binary` (y de cada archivo fuente no seguido) para identificar también los
cambios locales. No basta el SHA del commit si el árbol está modificado.
Registrar versión de Python, dependencias (`pip freeze` revisado sin secretos),
SDK/archivo/library hash, arquitectura, configuración efectiva **sin secretos**
y hora UTC. No publicar estos datos automáticamente.

Cada caso tiene estado PASS, FAIL, BLOCKED o NOT_RUN; comando, duración, esperado,
observado, medidas con unidades y evidencia relativa. El informe final usa
[el esquema JSON](hardware-report.schema.json). Nunca sustituir un resultado
medido por el de un simulador. Solo PASS si se cumplen **todos** los criterios
del caso; BLOCKED si falta acceso, permiso, dependencia o instrumento de medida.

### Reanudación

Leer el informe y verificar identidad/configuración/hashes antes de continuar.
No sobrescribir capturas ni volver a ejecutar movimientos porque falte una
respuesta. Conservar el run anterior y abrir otro si cambió el escenario.
Las pruebas fallidas no se “arreglan” cambiando umbrales ni modificando código
durante la validación; abrir una tarea aparte y repetir desde las puertas
afectadas tras la corrección.

## 3. Matriz ordenada de ejecución

Los límites temporales son presupuestos de prueba del proyecto, no garantías
del fabricante. Si una llamada nativa supera su timeout, no cerrar la cámara
desde otro hilo ni matar el proceso automáticamente: avisar, esperar al
operador y registrar FAIL. El STOP físico no depende de que este hilo responda.

| ID | Prerrequisito / puerta | Procedimiento y criterio PASS | Límite / evidencia |
| --- | --- | --- | --- |
| H0.1 | G0 | Baseline Python, build, lint y cuatro E2E aislados en simulación, todos correctos. Los hardware tests deben quedar SKIPPED. | 10 min; logs y versión del árbol |
| H0.2 | H0.1 | Descarga oficial fijada, SHA256 exacto, estructura x64/ARM64 y prueba ABI si hay compilador/header. Cargar SDK en el anfitrión; separar bloqueo USB de fallo de carga de biblioteca. | 2 min; manifiesto, hash, JSON/error probe |
| H1.1 | H0, acceso/G0 | `uname -m` = x86_64/aarch64/arm64; `getconf LONG_BIT` = 64; ordenador y OS identificados; Python 3.11–3.13. Hora UTC fiable. | 1 min; comandos de identidad |
| H1.2 | H1.1, G1 si instala | Instalación y dependencias completas, biblioteca de la arquitectura correcta enlazada sin `not found`; usuario no root con acceso al nodo USB correcto. No instalar reglas globales sin revisar. | 10 min; `file`, `ldd`, identidad y permisos |
| H1.3 | H1.2 | USB negociado a 5000M o más en `lsusb -t`; reserva >=2 GiB más originales; temperatura CPU <80 °C. En Pi `get_throttled=0x0`; en x64 registrar sensor identificado y contadores de throttling antes/después si disponibles. Si falta telemetría requerida, BLOCKED, no inventar cero. | 1 min; estado USB/disco/temperatura |
| H2.1 | H1, G0 | Probe nativo devuelve SDK 3.10.1 y Mars-M mono/Mars-C color esperada; serial coincide, USB3 true, dimensiones/ADC registrados. Descriptor USB no sustituye modelo leído por SDK. Ninguna apertura/exposición. | 15 s; probe JSON |
| H2.2 | H2.1 | Configurar `player_one`, serial exacto, RAW16, cámara sola, montura simulada y movimiento false. Revisar configuración efectiva antes de arrancar. Sin fallback. | 2 min; entorno local redactado |
| H3.1 | H2, G2 para 100 frames/50 ms | Banco de cámara opt-in: conexión, exposición 50000 µs/ganancia 100 con readback exacto, full frame bin1; 100 PNG uint16 variables; preview uint8 mono o BGR según sensor; Bayer conservado en original color; 0 errores; p95 <=2.55 s, ningún frame >5.05 s. | 10 min; originales, hashes y camera-bench.json |
| H3.2 | H3.1, G2 renovada | API con cámara real y montura simulada: sesión, 30 previews sin crear archivos, 3 capturas distintas, descarga original uint16 idéntica por SHA256; preview uint8. Configurar 10/50/200 ms y comprobar readback; restaurar 50 ms. | 5 min; JSON, archivos y conteos |
| H3.3 | H3.2, G5 USB | Con montura no conectada y cámara inactiva, el operador retira USB. Una captura debe fallar explícitamente, sin frame sintético. El operador reconecta; agente cierra/reconecta explícitamente y obtiene una captura. Sin bucle de reintento. | 3 min; errores, intervención y recuperación |
| H4.1 | H3, G3 | Cámara cerrada. Montura inmóvil, sin SynScan concurrente. `skywatcher_udp`, motion false, max step 0.1°. Conectar devuelve versiones/pasos/timers de ambos ejes, sin movimiento observado. | 30 s; handshake, firmware y observación humana |
| H4.2 | H4.1 | Orden de paso rechazada como `mount_motion_disabled`; STOP admite ACK de ambos ejes aun bloqueados. Confirmar visualmente inmovilidad; cierre también envía STOP y está incluido en G3. | 30 s; respuestas y tiempos |
| H5.1 | H4, G4 para este caso | Operador confirma zona segura, cables, trípode y apagado accesible. Habilitar motion solo para ensayo. Un paso +0.1° en azimut a <=0.25°/s; verificar eje/sentido y medir <=0.2° de recorrido real. STOP y confirmación presencial. | 30 s; aprobación, medición y vídeo/nota humana |
| H5.2 | H5.1, nueva G4 | Un paso +0.1° en altura y STOP, mismos criterios. Si no hay método para medir recorrido, BLOCKED. No inferir grados de la posición interna no calibrada. | 30 s; eje/sentido/medición/STOP |
| H5.3 | H5.2, nueva G4 | Un paso -0.1° en cada eje, **uno por vez**, con STOP entre ellos. Máximo acumulado de H5 <=0.4°. ACK de STOP en <=1 s en LAN sana; operador confirma reposo <=2 s tras STOP. Si el paso acabó antes, no afirmar frenado durante movimiento: registrarlo como no demostrado. | 1 min; tiempos, recorrido y observación |
| H6.1 | H5, G2+G3; motion false | Ambos drivers reales en API, estado/identidad inequívocos. Capturar 10 imágenes con montura inmóvil. Ningún movimiento, conflicto USB/UDP ni caída; repetir descarga/preview. | 5 min; estados, capturas, logs |
| H6.2 | H6.1, G2 de 30 min | Sesión prolongada de cámara con montura conectada pero bloqueada: >=30 min, >=100 capturas, 0 errores; p95 <=2.55 s; disco conserva reserva; temperatura <80 °C y throttling 0x0; crecimiento RSS <=max(128 MiB,25% del RSS tras 5 min). | 35 min; series cada 10 s, logs, hashes y métricas |
| H7.1 | H6, móvil/TLS | Pixel: TLS sin advertencias, autenticación, instalación PWA, responsive/modo rojo y descarga real. Sin Internet pero con LAN, control/cámara siguen operativos. | 10 min; capturas, navegador/OS, red |
| H7.2 | H7.1, G5 red/reinicio | Con motores bloqueados e inmóviles, operador pierde/restaura enlace móvil-Pi. UI muestra pérdida y no encola/reproduce órdenes. Reinicio limpio autorizado del servicio restaura sesión/archivos según configuración, pero deja dispositivos desconectados. | 5 min; UI, logs, identidad y estado tras reinicio |
| H8.1 | Todas las fases | Preview parado, cámara cerrada, STOP ambos ejes, confirmación humana de reposo, motion false persistido y backend de pruebas parado. Informe completo y sin secretos. | 2 min; estado final y report.json/report.md |

H5 comprueba movimiento de baja amplitud y STOP sobre ese recorrido; **no valida
todavía una parada de emergencia a velocidad alta**. No incrementar el
recorrido para “hacer visible” el movimiento sin un plan nuevo aprobado.
Los 0.2° son un límite superior conservador provisional, no precisión
astronómica certificada. Sin instrumentación, no emitir PASS del recorrido.

Para armar H5, cerrar primero los dispositivos y obtener aprobación para cambiar
el flag y reiniciar el backend de banco. Tras el reinicio, volver a identificar
configuración/handshake y renovar G3/G4 **antes** del primer paso; el permiso
anterior al reinicio no sirve. Renovar G4 para cada caso sin más cambios de
configuración. Al acabar, cerrar, persistir false y reiniciar/verificar el
backend antes de H6. Si reiniciar implica otra sesión, registrar un sub-run
enlazado y renovar las puertas: nunca eludir su caducidad.

### H0/H2: SDK y comandos de lectura

```bash
TELESCO_PI_DEVICE_MODE=simulator \
TELESCO_PI_CAMERA_DRIVER=simulated \
TELESCO_PI_MOUNT_DRIVER=simulated \
TELESCO_PI_MOUNT_MOTION_ENABLED=false \
TELESCO_PI_RUN_HARDWARE_CAMERA=0 \
.venv/bin/python -m pytest -q
cd apps/frontend
npm run lint
npm run build
npm run test:e2e
cd ../..
.venv/bin/python infra/scripts/fetch_player_one_sdk.py
.venv/bin/python -m libs.devices.player_one_sdk \
  --sdk-root .local-sdk/player-one/PlayerOne_Camera_SDK_Linux_V3.10.1
```

El descargador no sobrescribe un SDK existente. Si ya está descargado, verificar
su SHA256 y usar el probe; no borrar ni volver a extraer sobre él.
El entorno de H0 fuerza simulación y desactiva el banco físico aunque exista
una configuración local de hardware. No cargar el entorno de banco antes de H0.
URL, versión y hash están en
[el manifiesto fijado](../../infra/configs/player-one-sdk.json).
La descarga oficial Linux incluye ARM64; Nncam no controla la Mars-M.

En el Linux anfitrión, revisar con herramientas presentes (no instalar sin G1):

```bash
uname -m
getconf LONG_BIT
cat /etc/os-release
id
lsusb -t
df -B1 .
file .local-sdk/player-one/PlayerOne_Camera_SDK_Linux_V3.10.1/lib/arm64/libPlayerOneCamera.so.3.10.1
ldd .local-sdk/player-one/PlayerOne_Camera_SDK_Linux_V3.10.1/lib/arm64/libPlayerOneCamera.so.3.10.1
```

En x64 sustituir `lib/arm64` por `lib/x64`. `vcgencmd measure_temp` y
`vcgencmd get_throttled` se usan solo en Raspberry. En un PC identificar
sensores por su `type` en `/sys/class/thermal` o herramienta disponible,
y documentar fuente/unidades. No instalar utilidades ni modificar sensores
para ocultar un bloqueo.

### H3.1: banco reproducible de cámara, nunca de montura

Revisar [la plantilla](../../infra/configs/hardware-test.env.example) y cargar
solo sus valores concretos revisados en el entorno de **este proceso**.
Para H3, usar `TELESCO_PI_MOUNT_DRIVER=simulated`. No ejecutar sobre un backend
que ya tenga abierta la misma cámara. Obtener G2 antes de activar el opt-in:

```bash
# SOLO después de aprobación G2, con serial/SDK y entorno ya revisados:
TELESCO_PI_RUN_HARDWARE_CAMERA=1 \
TELESCO_PI_HARDWARE_EVIDENCE_DIR=/RUTA/NUEVA/RUN_ID/camera \
.venv/bin/python -m pytest tests/hardware/test_player_one_camera.py -q
```

El banco verifica Linux de 64 bits, selección `configured/player_one`, serial explícito,
RAW16 y movimiento deshabilitado. Solo instancia el driver de cámara; nunca
crea una montura. Conserva originales y `camera-bench.json`, incluso si falla
tras crear el directorio. Un frame constante es FAIL y requiere inspección,
no autoriza descubrir el objetivo ni manipular óptica automáticamente.

Para H6.2 mantener el backend integrado y medir sus capturas vía API; **no**
abrir la cámara simultáneamente con el banco directo. El banco admite
`TELESCO_PI_HARDWARE_FRAMES` (1–1000) e
`TELESCO_PI_HARDWARE_INTERVAL_SECONDS` (0–10) para una prueba de cámara aislada
prolongada, que no sustituye H6.2. No se anuncia FPS planetario ni pérdida de
frames de vídeo: este adaptador usa exposiciones individuales.

### H3.2/H6: contratos API y evidencias

Backend aislado en loopback, con directorio de datos nuevo y sin servicio
competidor. Seguir [el despliegue](../deployment/raspberry-pi.md), no instalarlo
en producción como parte de una prueba. Desde el propio anfitrión usar
`http://127.0.0.1:8000/api/v1`; desde móvil usar el proxy TLS autorizado.

1. `GET /devices`: comprobar `implementation=real` en cámara, SDK y
   configuración; en H6 ambos dispositivos deben ser reales. Un texto “real”
   por sí solo no prueba hardware: enlazar con serial/probe y handshake.
2. `POST /devices/camera.primary/connect`; comprobar HTTP y `accepted=true`.
3. `POST /sessions` con `{"name":"hardware-RUN_ID"}`; guardar `session.id`.
4. `POST /devices/camera/configure` con
   `{"configuration":{"exposure_ms":50,"gain":100}}`; guardar respuesta y estado.
5. `POST /devices/camera/preview/start`; 30 veces
   `GET /devices/camera/preview/frame`, con intervalo >=1 s. Decodificar
   PNG/uint8 y comparar `GET /sessions/files` antes/después: sin nuevos archivos.
6. `POST /devices/camera/capture` con
   `{"session_id":"ID_REAL","name_prefix":"hardware"}`; repetir 3 veces.
   Respuestas incluyen `file` y `preview`. Descargar ambos mediante
   `GET /sessions/files/{file_id}/content`; original uint16, preview uint8.
   Comparar SHA256 original descargado con el archivo indexado local seguro,
   dimensiones de la Mars-M y nombres distintos. No resolver rutas arbitrarias.
7. `POST /devices/camera/preview/stop`, luego cerrar cámara explícitamente.
   En integración, cerrar montura solo bajo G3: el cierre envía STOP.

En cada POST, un HTTP 200 con `accepted=false` es FAIL. Registrar respuestas
409 estructuradas y `request_id`, sin considerarlas una captura.
Para H4/H5 usar los cuerpos/rutas del
[contrato de dispositivos](../api/devices.md), empezando por
`{"delta_azimuth":0.1,"delta_altitude":0}` solo tras G4.
Comprobar que la UI muestra el paso efectivo de 0.1° antes de usarla; no
aceptar una configuración de 1°/5° en este banco.

### H6.2: método de medición

Tras 5 min de calentamiento, tomar RSS del PID Uvicorn/backend cada 10 s
(`ps -o rss= -p PID`, KiB), temperatura y `get_throttled`; repetir hasta >=30 min.
Registrar espacio libre antes/después, número de capturas, fallos y latencias
con reloj monotónico. Medir captura desde POST hasta respuesta JSON y descarga
aparte; p95 con percentil 95 de todas las capturas, no promedio ni mejor caso.
Guardar al menos 100 originales y sus hashes; presupuestar espacio antes.
Si el intervalo impide completar 100, ampliar solo dentro de los 35 min
autorizados; si no, FAIL. No medir RSS del cliente como si fuera backend.

## 4. Aborto, cierre y fallos deliberados

- Nadie deja el banco moviéndose o con autorización indefinida. Trípode/cables
  despejados, óptica segura y acceso físico a alimentación. Nunca apuntar al Sol.
- STOP disponible desde PWA y acceso local; un ACK no certifica parada física.
  Ante sentido erróneo, atasco o ruido inesperado: STOP, intervención presencial,
  marcar FAIL y **no reintentar**. Si no hay enlace, el operador asegura el equipo.
- Un timeout de montura cierra el socket; no reconectar ni repetir la orden
  porque podría haberse ejecutado. No ensayar pérdida de WiFi moviendo motores.
- Desconexión USB, pérdida de red y reinicio solo por acción coordinada con el
  operador (G5), con cámara inactiva y motores inmóviles. Nunca apagar la Pi
  durante escritura ni provocar disco lleno real. Los fallos sintéticos de
  almacenamiento/simulador se prueban en H0, no se acreditan como fallos físicos.
- Restauración tras reinicio: registrar valor de
  `TELESCO_PI_AUTO_RESTORE_LAST_SESSION`; para el caso de restauración usar true
  tras revisión. El template de banco usa false para no abrir sesiones previas.
  En ambos casos los dispositivos deben permanecer desconectados.
- Al salir, desactivar movimiento en configuración y proceso antes de ceder
  el equipo. Si no puede verificarse cierre/reposo, el informe final debe
  destacarlo, pedir al operador asegurar físicamente y no declarar éxito.

## 5. Criterio de entrega

PASS global requiere H0.1–H8.1 completos, evidencias y confirmaciones físicas,
sin casos obligatorios BLOCKED/NOT_RUN. Se permiten entregas parciales con
estado global BLOCKED o FAIL, identificando la puerta pendiente.
En `report.md`: tabla por caso, métricas real/umbral, incidentes, aprobaciones,
estado final, riesgos no probados y siguiente acción. En `report.json`:
identidad reproducible y datos estructurados del esquema.

Al preparar esta entrega se acredita el software y la carga x64 del SDK.
El dispositivo local anuncia Mars-C por USB pero no permite acceso RW al
usuario actual; no se acredita apertura/captura. La consulta de montura a la
dirección prevista no respondió. ARM64, adquisición, motores, Pixel y sesión
prolongada permanecen pendientes de acceso y supervisión. Ver
[instalación Linux](../deployment/linux-installer.md) y
[matriz de soporte](../architecture/adding-device-drivers.md).
