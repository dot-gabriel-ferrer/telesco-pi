# Instalación y distribución Linux

## Alcance de 0.2.0

Estación local para **Linux x86_64 o ARM64**, Python **3.11–3.13**:
PWA y API en un solo proceso/origen, sesiones, catálogo/planner, preview,
captura y descarga. Simulador por defecto; Player One Mars-M/Mars-C y Nncam
opcionales, SkyWatcher UDP con motores bloqueados por defecto.
No requiere Raspberry para desarrollar ni usar la aplicación.

Las funcionalidades científicas avanzadas del roadmap (solve calibrado,
vídeo planetario, EAA continuo y seguimiento orbital físico) **no están
terminadas ni habilitadas**. No usar con óptica solar ni motores desatendidos.
Las bibliotecas científicas existentes no se presentan como flujos operativos.

## Desde el repositorio

Se necesita Git, Python compatible con `venv/pip`, Node.js 20.19+ o 22.12+ y npm para
construir. El sistema también debe aportar las bibliotecas nativas requeridas
por Python/OpenCV y `libusb-1.0.so.0` si se usa Player One.

```bash
git clone https://github.com/dot-gabriel-ferrer/telesco-pi.git
cd telesco-pi
python3.11 install.py
~/.local/bin/telesco-pi serve
```

Abrir **http://127.0.0.1:8000**. Ctrl+C cierra el proceso y los dispositivos.
El instalador no pide sudo, no inicia motores ni servicios y no cambia la red.
Crea un venv por versión y enlaza el ejecutable en `~/.local/bin`.
Si ese directorio no está en PATH, usar la ruta completa anterior.
Usar `--no-path-link` para no crear el enlace o `--prefix RUTA` para otra
ubicación. Nunca ejecutar como root. No usar Python 3.14 con los pins actuales.

La instalación desde fuentes construye la UI y descarga las dependencias.
No es una instalación offline ni requiere que exista el `.venv` de desarrollo.
Un fallo de construcción/dependencias es un error visible: no se activa una
versión incompleta y se conserva la versión previa.

## Desde un paquete de release

```bash
sha256sum -c telesco-pi-0.2.0-linux.tar.gz.sha256
tar -xzf telesco-pi-0.2.0-linux.tar.gz
cd telesco-pi
python3.11 install.py
~/.local/bin/telesco-pi doctor
~/.local/bin/telesco-pi serve
```

El paquete contiene una wheel con UI/catálogos, instalador y constraints
de dependencias, licencia, procedencia de construcción y checksums.
**Node.js/npm no son necesarios para instalar una release.**
Descargar únicamente de una fuente de confianza: los hashes detectan corrupción,
no autentican a quien distribuye el instalador. Revisar la licencia existente:
no se otorga aquí una licencia abierta ni se cambian derechos del propietario.

Para preparar la release (desde el entorno de desarrollo instalado):

```bash
.venv/bin/python infra/scripts/build_release.py --output .release/0.2.0
```

Para un destino sin Internet:

```bash
.venv/bin/python infra/scripts/build_release.py \
  --output .release/offline-x64-py311 --wheelhouse
```

Esa variante descarga wheels de **la arquitectura y versión Python de
construcción**. No copiar una wheelhouse x64 a ARM64: construir la variante
ARM64 en ARM64, o usar la release normal con Internet en la Pi.
En destino ejecutar `python3.11 install.py --offline`.
El SDK del fabricante no se incluye en ninguna release: obtenerlo aparte,
conservar su licencia y preparar su descarga antes de ir sin Internet.

## Configuración persistente y operación

El archivo de configuración es JSON en
`~/.config/telesco-pi/config.json`; datos/capturas en
`~/.local/share/telesco-pi/data`. Se respetan XDG_CONFIG_HOME/XDG_DATA_HOME.
`telesco-pi --config RUTA ...` permite instancias separadas. Un puerto/datos
distintos son obligatorios si se ejecutan dos instancias.

```bash
telesco-pi doctor
telesco-pi configure --simulator
telesco-pi serve --port 8000
```

`configure` nunca conecta hardware y siempre vuelve a bloquear motores.
Cambiar configuración con el proceso parado y reiniciarlo para aplicarla.
El lanzador no carga `.env` ni variables TELESCO_PI_* del entorno; usa
exclusivamente el JSON y los valores por defecto de Settings.
No guardar tokens, passwords ni claves privadas en la configuración compartida.

Para Player One, con permiso para descargar el SDK oficial:

```bash
telesco-pi sdk-install
telesco-pi configure --camera player_one \
  --sdk-root ~/.local/share/telesco-pi/sdk/player-one/PlayerOne_Camera_SDK_Linux_V3.10.1
telesco-pi doctor --sdk-probe
# Tras obtener el serial exacto en el probe:
telesco-pi configure --camera-id SERIAL_REAL
telesco-pi serve
```

El probe no abre ni expone. En la UI conectar cámara, iniciar sesión y preview.
Elegir `mount=simulated` hasta validar separadamente la montura.
El original color es mosaico Bayer RAW8/RAW16 en PNG sin pérdida; el preview
hace demosaicing para navegador. No equivale a una imagen calibrada ni FITS.
El serial y el patrón se guardan en metadatos de captura.

### Permisos USB

Si `doctor` indica `read_write_access=false`, no repetir capturas ni ejecutar
como root. Un administrador debe revisar e instalar una regla **acotada al
producto y grupo autorizado**. Para el dispositivo visto en este ordenador,
vendor `a0a0`, producto `4620`, el fichero de ejemplo está en el repositorio:
`infra/configs/70-telesco-pi-player-one.rules`.
Confirmar IDs con `lsusb` antes de usarlo. La regla concede `0660` al grupo
`plugdev`; el usuario debe pertenecer a ese grupo. No concede `0666`, no altera
`usbfs_memory_mb` ni instala permisos automáticamente.

Un administrador puede instalar la regla revisada, recargar udev y volver a
conectar la cámara inactiva. No manipular dispositivos ajenos, no cambiar
permisos globalmente. El SDK puede contar una cámara sin permisos y fallar al
leer sus propiedades: no significa “cero cámaras” ni éxito del driver.

### Montura y acceso desde móvil

```bash
telesco-pi configure --mount skywatcher_udp --mount-host IP_CONFIRMADA
```

La montura y el ordenador deben compartir una ruta de red válida. No se
reconfigura el WiFi automáticamente. El valor típico `192.168.4.1` no garantiza
que sea alcanzable desde la red doméstica. No escanear redes ni probar IPs
ajenas. Conectar consulta parámetros; cerrar/STOP sí manda comandos de parada.
Habilitar movimiento requiere editar explícitamente `mount_motion_enabled`,
presencia humana y el protocolo de banco, no basta tener la montura encendida.

El lanzador distribuido solo escucha en loopback. Para móvil usar un proxy
HTTPS autenticado en LAN según la guía Raspberry/Linux del repositorio; no
exponer Uvicorn directamente ni reenviar puertos a Internet. Una instalación
de localhost es usable y offline una vez instaladas las dependencias, pero
no constituye validación Pixel/TLS.

## Actualización, rollback y servicio opcional

Parar la aplicación antes de actualizar y respaldar datos/configuración con
los dispositivos cerrados. Ejecutar el nuevo instalador con el mismo prefijo:
no sobrescribe configuración ni borra capturas. Cada instalación tiene venv
propio; `current` se cambia solo después de pip check y smoke del paquete.

```bash
python3.11 install.py --rollback
```

Intercambia `current` y `previous`; no retrocede SQLite ni elimina datos.
Las migraciones incompatibles futuras requerirán un procedimiento específico.
Un fallo deja su carpeta en `releases` para diagnóstico; no borrar versiones
en uso ni eliminar el prefijo entero porque contiene datos.

Servicio **opcional**, administrado por el usuario y sin root:
copiar `infra/systemd/telesco-pi-user.service` a
`~/.config/systemd/user/telesco-pi.service`, comprobar su ruta de instalación y:

```bash
systemctl --user daemon-reload
systemctl --user enable --now telesco-pi
systemctl --user status telesco-pi --no-pager
journalctl --user -u telesco-pi -n 100 --no-pager
```

Desactivar con `systemctl --user disable --now telesco-pi`.
No inicia automáticamente ninguna conexión hardware. No activar linger sin
revisar las implicaciones de dejar equipo funcionando sin sesión presencial.
Para desinstalar, parar/deshabilitar servicio y retirar únicamente el enlace y
versiones revisadas; conservar o exportar datos y configuración expresamente.
