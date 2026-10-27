# Despliegue local en Raspberry Pi 5

Para una instalación de usuario sin root, en Raspberry **o en otro Linux**,
usar primero [el instalador Linux](linux-installer.md). La guía siguiente
describe el despliegue de sistema opcional, administrado y con proxy LAN.

## Requisitos

- Raspberry Pi OS de 64 bits; Python 3.11–3.13 y Node.js 20+.
  Los pins actuales de Pydantic no soportan Python 3.14.
- Red local dedicada; no exponer puertos al exterior ni usar port forwarding.
- Cámara identificada por modelo/SDK y montura accesible en la red de la Pi.
- Para Nncam: módulo Python y biblioteca nativa ARM64 autorizados por el
  proveedor, más sus reglas udev. No ejecutar el backend como root.

## Instalación

Desde una copia del repositorio en `/opt/telesco-pi`, crear un entorno virtual
y construir la interfaz **antes** de activar el servicio:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
cd apps/frontend
npm ci
npm run build
cd ../..
```

Crear el usuario de servicio y el directorio de configuración con las
herramientas de administración del sistema. Debe poder leer el repositorio,
ejecutar el entorno virtual y acceder a la cámara según las reglas udev del
proveedor. `StateDirectory` crea el directorio de datos persistentes con el
propietario correcto.

Copiar [el entorno de ejemplo](../../infra/configs/telesco-pi.env.example) a
`/etc/telesco-pi/telesco-pi.env` y [la unidad](../../infra/systemd/telesco-pi.service)
a `/etc/systemd/system/telesco-pi.service`. Revisar rutas y permisos antes de:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now telesco-pi
curl --fail http://127.0.0.1:8000/api/v1/health/ready
sudo journalctl -u telesco-pi -n 100 --no-pager
```

El servicio permanece en loopback. La configuración empieza en simulación y no
conecta ni mueve automáticamente hardware al arrancar.

## Acceso móvil, HTTPS y PWA

[La configuración Nginx](../../infra/configs/nginx.conf) sirve el build y
proxifica REST/WebSocket en el mismo origen. Requiere:

1. Resolver `telesco-pi.local` a la IP local de la Pi (mDNS o DNS local).
2. Instalar un certificado válido para ese nombre y su clave en las rutas TLS
   indicadas. Para una CA local, instalar su certificado de confianza en el
   móvil; no ignorar advertencias TLS.
3. Crear `/etc/telesco-pi/htpasswd` con una contraseña propia usando `htpasswd`;
   permitir su lectura a Nginx, no al resto de usuarios.
4. Revisar `nginx -t` y recargar Nginx. No arrancarlo con certificados de ejemplo.
   Añadir `telesco-pi.local` a `TELESCO_PI_TRUSTED_HOSTS` (o `trusted_hosts`
   en el JSON del lanzador) para que el backend acepte el Host del proxy.
5. Abrir `https://telesco-pi.local`, autenticarse e instalar la PWA.

El backend no incorpora autenticación activa por defecto; el despliegue
propuesto exige HTTPS + autenticación en el proxy. No publicar directamente
Uvicorn en una red compartida. La PWA cachea recursos de interfaz, no comandos,
imágenes de cámara ni respuestas API. Sin Internet puede seguir observando en
la red local; sin conexión a la Pi no puede controlar hardware.

## Activar Nncam / Photsat

Photsat utiliza EHD/Nncam, **no el SDK Player One**. No configurar `nncam` para
una Mars M sin confirmar compatibilidad con el fabricante. La integración no
importa PyQt, no ejecuta `main.py` de Photsat y no incorpora su binario.

Instalar de forma autorizada el paquete que permita importar `nncam.nncam`,
incluida su biblioteca nativa para la arquitectura de la Pi. Si se instala fuera
del entorno virtual, definir `PYTHONPATH` al directorio que contiene el paquete
`nncam`. Comprobar el binario con `file` y las dependencias con las herramientas
del proveedor: el `.so` incluido en otro repositorio no garantiza ARM64.

```ini
TELESCO_PI_DEVICE_MODE=configured
TELESCO_PI_CAMERA_DRIVER=nncam
TELESCO_PI_CAMERA_SDK_MODULE=nncam.nncam
TELESCO_PI_MOUNT_DRIVER=simulated
```

Si se enumeran varias cámaras, fijar `TELESCO_PI_CAMERA_ID`. Para obtener los
identificadores, con el SDK autorizado ya instalado:

```bash
.venv/bin/python -c 'from nncam.nncam import Nncam; print([(c.id, c.displayname) for c in Nncam.EnumV2()])'
```

La entrega usa RAW8, imagen completa y binning 1; guarda PNG monocromo sin pérdida.
No equivale a una captura científica RAW16/FITS. Las exposiciones se expresan en
ms en la API y se convierten a µs para Nncam; la ganancia se valida contra el
rango del dispositivo. Si falta SDK o hardware, aparece un error, no simulación.

## Activar Player One Mars-M

Obtener el SDK oficial Linux **3.10.1** desde la raíz del repositorio:

```bash
.venv/bin/python infra/scripts/fetch_player_one_sdk.py
.venv/bin/python -m libs.devices.player_one_sdk \
  --sdk-root .local-sdk/player-one/PlayerOne_Camera_SDK_Linux_V3.10.1
```

El primer comando verifica el SHA256 fijado en
[el manifiesto](../../infra/configs/player-one-sdk.json) y extrae a `.local-sdk/`
(ignorado en Git), sin instalar permisos ni ejecutar muestras. No sobrescribe
un SDK existente. El segundo **solo enumera**; no abre ni expone.
En Linux aarch64 se selecciona `lib/arm64/libPlayerOneCamera.so.3.10.1`; en
x86_64, `lib/x64/`. No se admite Linux de 32 bits en este adaptador.

SHA256 del paquete:
`d683a7a793846b35c5de82f7cfab9e7a12a911f0b99f9e5dbf653ba0300f2886`.
Es un hash calculado de la descarga HTTPS, no una firma publicada del fabricante.
Conservar `license.txt` y los avisos del paquete; los binarios/cabeceras del
proveedor no se incorporan al repositorio.

En la Pi comprobar dependencias con `ldd`: `libusb-1.0.so.0`,
`libstdc++.so.6`, `libm.so.6`, `libgcc_s.so.1` y `libc.so.6`. Instalar paquetes
faltantes solo tras identificar el error y obtener autorización de administración.
Revisar permisos del nodo USB para el usuario de servicio, no ejecutar como root.
Las reglas udev del SDK conceden `0666` y modifican globalmente memoria USB:
**no copiarlas automáticamente**. Preferir regla restringida al dispositivo,
grupo de servicio autorizado y `MODE=0660`; cualquier ajuste global requiere
revisión expresa. No desactivar el aislamiento de systemd para sortear permisos.

```ini
TELESCO_PI_DEVICE_MODE=configured
TELESCO_PI_CAMERA_DRIVER=player_one
TELESCO_PI_PLAYER_ONE_SDK_ROOT=/opt/telesco-pi/.local-sdk/player-one/PlayerOne_Camera_SDK_Linux_V3.10.1
TELESCO_PI_PLAYER_ONE_BIT_DEPTH=16
TELESCO_PI_CAMERA_ID=SERIAL_OBTENIDO_EN_EL_PROBE
TELESCO_PI_MOUNT_DRIVER=simulated
TELESCO_PI_MOUNT_MOTION_ENABLED=false
```

Comenzar con cámara sola. Conectar requiere aprobación para abrir/configurar la
cámara. El adaptador valida Mars-M monocroma, formato, exposición/ganancia y
readback; no acepta ROI ni binning diferente de 1. Exposiciones en API en ms,
convertidas a µs en SDK. Original RAW16 en PNG uint16 sin pérdida, profundidad
ADC independiente registrada en metadatos; preview convertido a uint8.
RAW8 se elige explícitamente con `TELESCO_PI_PLAYER_ONE_BIT_DEPTH=8`.
No es captura FITS ni secuencia/vídeo planetario; el preview usa single shots.
Los errores dejan el dispositivo en error y requieren cierre/reconexión explícitos.
Sin SDK/cámara hay error visible, nunca fallback al simulador.

Seguir [el plan del agente](../testing/hardware-agent-plan.md), no las muestras
del proveedor (pueden activar funciones como ST4).

## Activar SkyWatcher

```ini
TELESCO_PI_DEVICE_MODE=configured
TELESCO_PI_MOUNT_DRIVER=skywatcher_udp
TELESCO_PI_MOUNT_HOST=192.168.4.1
TELESCO_PI_MOUNT_PORT=11880
TELESCO_PI_MOUNT_MAX_STEP_DEG=0.1
TELESCO_PI_MOUNT_MOTION_ENABLED=false
```

El protocolo se basa en mensajes de controladora de ejes referenciados en
[skywatcher_open](https://github.com/skywatcher-pacific/skywatcher_open).
Conectar primero consulta versión, pasos por revolución y temporizador en ambos
ejes; **no calibra una posición celeste**.

En banco y con aprobación presencial para cada caso, habilitar movimiento
temporalmente (`TELESCO_PI_MOUNT_MOTION_ENABLED=true`) y comprobar pasos de
0.1° y STOP según el plan. Deshabilitarlo al cerrar. Con false, cualquier
paso se rechaza como `mount_motion_disabled`; STOP sigue disponible.
Velocidad acotada a 0,25°/s; movimiento relativo
finito, sin reintentos automáticos de órdenes. El control rechaza nuevos pasos
si un eje está en movimiento. No usar simultáneamente SynScan u otro cliente.
Una pérdida de enlace cierra el socket para descartar respuestas tardías; no
prueba que la montura esté detenida. Debe existir acceso físico al equipo.

GoTo absoluto, PARK y seguimiento altazimutal no están habilitados. Requieren
calibración, límites mecánicos y un lazo de control validado.

## Validación y recuperación

Seguir [la guía de pruebas](../testing/device-integration.md) y las puertas del
[plan](../product/development-plan.md). La sesión se restaura desde SQLite;
los dispositivos no se reconectan automáticamente tras reiniciar. Reconectar
explícitamente desde la PWA, comprobar estado y después reactivar el preview.
El apagado normal intenta STOP en ambos ejes y cierra la cámara. No puede
garantizar parada frente a corte de corriente, pérdida de red o SIGKILL.
