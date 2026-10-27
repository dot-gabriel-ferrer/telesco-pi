# Dispositivos y flujo de observación

Base: `/api/v1`. Ver también OpenAPI en `/api/v1/docs`.
Los comandos devuelven `{accepted, status, message, payload}`. HTTP 200 no
significa que se haya aceptado una orden: comprobar `accepted`. Los stubs
rechazan las operaciones y anuncian capacidades deshabilitadas.

| Método | Ruta | Función |
| --- | --- | --- |
| GET | `/devices` | Estado, implementación, capacidades y metadatos de cada driver |
| POST | `/devices/{device_id}/connect` | Conexión explícita |
| POST | `/devices/{device_id}/disconnect` | Cierre; STOP antes de cerrar la montura real |
| POST | `/devices/mount/manual-slew` | Paso relativo finito |
| POST | `/devices/mount/stop` | Solicitar STOP en ambos ejes |
| POST | `/devices/camera/configure` | Configurar exposición/ganancia |
| POST | `/devices/camera/preview/start` | Habilitar preview |
| GET | `/devices/camera/preview/frame` | PNG actual, `Cache-Control: no-store` |
| POST | `/devices/camera/preview/stop` | Deshabilitar preview |
| POST | `/devices/camera/capture` | Guardar original y PNG de preview en una sesión activa |
| GET | `/sessions/{session_id}/files` | Archivos indexados de una sesión |
| GET | `/sessions/files` | Todos los archivos indexados |
| GET | `/sessions/files/{file_id}/content` | Descargar un archivo indexado existente |

Identificadores de dispositivos: `mount.primary` y `camera.primary`.
El PNG de preview no requiere una sesión, no se indexa ni se escribe al disco.
La PWA solicita un frame cada segundo después de recibir el anterior; no es
un canal de vídeo científico de alta velocidad. La captura sí requiere sesión.

## Ejemplos de cuerpos JSON

Paso de banco de 0.1 grados en azimut (solo tras autorización presencial):

```json
{"delta_azimuth": 0.1, "delta_altitude": 0}
```

Configuración de cámara:

```json
{"configuration": {"exposure_ms": 50, "gain": 100}}
```

Captura en la sesión activa:

```json
{"name_prefix": "luna"}
```

El prefijo admite 1–64 caracteres ASCII alfanuméricos, `_` y `-`. Se genera un
nombre único por captura. Puede indicarse `session_id`, pero debe corresponder
a una sesión activa existente.

Nncam valida rangos del SDK y solo admite full-frame y binning 1. El simulador
conserva la captura PGM; su preview se transforma a PNG. Nncam guarda RAW8 en
PNG monocromo; no se anuncia soporte RAW16 ni secuencias.

Player One Mars-M usa su SDK oficial, no Nncam; guarda RAW16 en PNG uint16
por defecto (RAW8 configurable). El preview se convierte a uint8 sin alterar
el original. Metadatos distinguen `bit_depth` del contenedor de
`sensor_adc_bit_depth`. Full-frame, binning 1, exposición/ganancia manuales con
readback del SDK, sin secuencias ni vídeo de alta velocidad.

En SkyWatcher real, `TELESCO_PI_MOUNT_MOTION_ENABLED=false` por defecto:
`supports_manual_slew=false` y rechazo `409 mount_motion_disabled`.
STOP y consultas siguen disponibles; el simulador no está afectado.
El cierre de montura y apagar seguimiento también envían STOP.

## Errores

Formato: `{error, code, request_id, details}`.

- `404`: dispositivo o archivo desconocido/no disponible.
- `409`: falta conexión/sesión, preview inactivo, timeout, SDK ausente, comando
  rechazado o capacidad no implementada.
- `422`: configuración o entrada fuera del contrato.
- `507 storage_full`: no se pudo escribir la captura por falta de espacio.

GoTo y seguimiento conservan sus rutas existentes, pero el adaptador SkyWatcher
rechaza GoTo absoluto y seguimiento distinto de OFF. PARK no tiene endpoint y
aparece deshabilitado en la interfaz. No se simula una parada confirmada si el
enlace se pierde.

## Contexto del planificador

`POST /astronomy/plan` requiere una sesión activa. El backend vincula el
`session_id` real y el `request_id` de la petición al contrato científico.
Sin sesión devuelve `409 session_required`, no crea una sesión ficticia.
La PWA explica este requisito y muestra los errores del catálogo/planificador.

## Procesado de capturas indexadas

`POST /processing/planetary` trabaja sobre originales de una sesión activa,
sin abrir cámara ni enviar comandos a montura:

```json
{
  "session_id": "ID_DE_SESION_ACTIVA",
  "file_ids": ["ID_ORIGINAL_1", "ID_ORIGINAL_2"],
  "profile": "balanced"
}
```

Seleccionar entre 2 y 20 IDs distintos de tipo `capture`, todos de esa sesión,
misma cámara/serial, dimensiones, profundidad, exposición/ganancia/binning y
patrón Bayer. Solo PNG/PGM, máximo 16 megapíxeles por imagen, 64 MiB por archivo
y **32 MiB sumados como float32** antes de decodificar. Los límites son
conservadores para los buffers intermedios; no son una medida de RSS garantizada.

El pipeline existente puntúa nitidez/SNR empíricos, conserva los mejores
40/50/70% según `low/balanced/high` (mínimo uno), alinea por traslación,
apila, realza y normaliza contraste. Para Bayer/color procesa luminancia:
no presenta el resultado como RGB, fotometría calibrada, EAA continuo, vídeo
ni corrección de rotación de campo.

Devuelve `file` (PNG uint16), `array` (NPY float32 normalizado), `preview`
(PNG uint8), `selected_frames`, `total_frames` y `notes`. Los tres artefactos
se indexan y descargan por ID. Metadatos incluyen IDs fuente y procedencia
del generador; el simulador sigue siendo simulación. Originales intactos.

Desde **Archivos**, seleccionar casillas de originales y pulsar **Apilar**.
Solo un trabajo por proceso: `409 processing_busy` si ya hay otro.
`422` ante entradas incompatibles, constantes, inaccesibles o que superan
presupuesto; `507 storage_full` si falta disco. No reintentar automáticamente:
una desconexión HTTP puede dejar el trabajo completando y los artefactos ya
guardados. Consultar archivos antes de repetir. Un fallo de escritura parcial
se informa; conservar y reconciliar archivos antes de limpiar manualmente.
