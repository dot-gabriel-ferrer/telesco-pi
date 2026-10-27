# Validación de la iteración de dispositivos e interfaz

## Alcance y resultado

La iteración implementa los cinco bloques de software del
[plan mejorado](../product/development-plan.md): configuración, adaptadores,
API, interfaz y entrega reproducible. **No certifica la V1 física ni completa
las fases científicas avanzadas del roadmap original.**

| Comprobación | Resultado local / estado |
| --- | --- |
| Suite Python | 82 pruebas aprobadas en Linux x64; banco físico opt-in omitido (SKIPPED) sin permisos/equipo validado |
| Frontend | TypeScript + build de producción + ESLint sin errores |
| Playwright | 5 pruebas sobre el build de producción, no mocks de API |
| Responsive | Sin desbordamiento horizontal en 320, 390, 768 y 1440 px |
| Preview | PNG decodificable, cero archivos adicionales por frame |
| Persistencia | Sesión/archivos restaurados tras cerrar y recrear la aplicación; hardware desconectado |
| Errores | SDK ausente, enlace perdido, rango inválido, disco lleno y comandos rechazados visibles |
| systemd | Análisis de la unidad sustituyendo únicamente la ruta del Python de destino por la local |
| Nginx/TLS | Plantilla revisada; pendiente `nginx -t` con certificados y rutas del equipo de destino |
| SDK Player One | Linux 3.10.1 oficial descargado, SHA256 fijado, extracción repetida y carga x64 con 0 cámaras |
| ABI Player One | sizeof/offsets ctypes comparados con programa C compilado contra la cabecera oficial externa |
| Seguridad de movimiento | Montura real bloqueada por defecto; rechazo sin enviar movimiento y STOP aún disponible |
| Instalación Linux | Wheel con PWA/catálogos instalada en venv limpio; smoke de UI/API/capturas/descargas sin árbol de fuentes |
| Offline / actualización | Instalación desde wheelhouse x64/Python 3.11 con `--no-index`; actualización y rollback de ida/vuelta conservan configuración |
| Dependencias frontend | Vite 8 y dependencias compatibles; `npm audit` completo sin vulnerabilidades reportadas al verificar |
| Navegador instalado | Dashboard del paquete abierto y revisado visualmente; los cuatro E2E automatizados usan servidores de simulación aislados |

Una advertencia de deprecación de `anyio.abc.BlockingPortal` procede del
TestClient fijado en las dependencias. Al cortar la red o recargar durante una
conexión WebSocket, el proxy de Vite puede registrar `EPIPE`; la prueba exige
que la interfaz informe de la desconexión, no que el canal continúe operativo.

## Ejecutar de nuevo

Desde la raíz con Python 3.11–3.13:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
cd apps/frontend
npm ci
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

Detener antes los servidores manuales en los puertos 8000 y 5173.
Playwright arranca servidores propios, fuerza simulación y almacena datos de
prueba en `.runtime-data/e2e`. No reutiliza un backend que pudiera controlar
hardware real. La CI reproduce la misma secuencia; no se ejecuta contra equipos
físicos ni requiere credenciales.

## Cobertura

- [Drivers](../../tests/unit/test_device_drivers.py):
  protocolo de 24 bits little-endian, servidor UDP local con ACK/rechazo,
  pasos positivos/negativos, velocidad, estado ocupado, STOP en ambos ejes,
  timeout y cierre de socket. SDK Nncam falso con callback en un hilo real,
  padding de fila, conversión a PNG, exposición en µs, rangos, error/desconexión,
  falta de SDK, ambigüedad de selección, timeout y limpieza al fallar la apertura.
- [API](../../tests/integration/test_device_api.py):
  sesión, conexión, configuración, preview sin escrituras, capturas distintas,
  descarga, prefijos/rangos inválidos, enlace perdido, ausencia de fallback,
  almacenamiento lleno, restauración, enlaces simbólicos fuera del storage y
  contexto real de sesión/petición en el planificador.
- [Despliegue](../../tests/unit/test_deployment.py):
  análisis de unidad systemd sin instalar servicios ni requerir `/opt` en CI.
- [Player One](../../tests/unit/test_player_one.py):
  SDK falso, selección Mars-M/serial, lectura de exposición/ganancia, errores,
  cierre ante fallo, RAW8/RAW16 PNG y preview uint8, timeout, serialización y
  cancelación repetida sin cerrar durante acceso nativo; firmas ctypes y ABI C.
- [Descargador](../../tests/unit/test_player_one_download.py):
  hash, corrupción, rutas inseguras, host HTTPS final, rechazo de sobrescritura
  y extracción del archivo oficial cuando está disponible.
- [Banco físico de cámara](../../tests/hardware/test_player_one_camera.py):
  desactivado salvo opt-in explícito; comprobado localmente con SDK falso en
  éxito/fallo, sin presentarlo como prueba física.
- [CLI](../../tests/unit/test_linux_cli.py):
  configuración JSON atómica/0600, aislamiento frente a `.env` y variables
  TELESCO_PI, errores explícitos, diagnóstico de permisos, canales de Bayer,
  UI empaquetada y rutas de recarga, API desconocida y archivos privados no
  expuestos, rechazo de Host/Origin ajenos en HTTP/WebSocket.
- [Instalador](../../tests/unit/test_linux_installer.py):
  integridad/corrupción, rutas fuera de release, wheels offline verificadas,
  activación y rollback sin pérdida de archivos.
- [Smoke de instalación](../../infra/scripts/smoke_install.py):
  lanza el ejecutable instalado desde un directorio ajeno, crea configuración
  aislada, recorre UI/API/catálogos, preview sin archivos, 3 capturas/descargas
  y STOP simulado, y verifica cierre limpio.
- [Procesado operativo](../../tests/integration/test_processing_api.py):
  selección/alineado/apilado/exportación PNG16/NPY, hashes originales intactos,
  sesión/tipo/duplicados, memoria, configuraciones y profundidades distintas,
  archivos constantes, symlinks externos, disco lleno, exclusión mutua y
  cancelación que espera al worker antes de liberar recursos.
- [Navegador](../../apps/frontend/tests/observation.spec.ts):
  flujo móvil completo, descarga real, STOP independiente, modo rojo,
  dimensiones de imagen, responsive, modal/tecla Escape/restauración de foco,
  error visible de hardware, shell PWA offline y catálogo/planificador.

Se comprobó visualmente el dashboard en el navegador integrado, en móvil y
escritorio. El patrón del simulador es sintético; no se presenta como una foto
astronómica ni como señal de una cámara física.

## Pruebas que requieren el equipo

No ejecutadas: carga del binario ARM64, cámara USB real, firmware/enlace UDP AZ-Go2,
sentido físico de los motores, parada real, límites mecánicos, rendimiento en
Pi 5, Pixel/tethering, instalación PWA con TLS de confianza y sesión prolongada.
Seguir [el plan detallado para el agente](hardware-agent-plan.md) antes
de activar el adaptador real. No validar motores en un equipo desatendido.

El SDK Player One y su adaptador ya están preparados; no equivalen a hardware
certificado. Las pruebas ABI y extracción que requieren el SDK se omiten en CI
si el paquete externo no está disponible. El agente de banco es de invocación
manual y genera evidencias con [este esquema](hardware-report.schema.json).
Las herramientas científicas ya presentes no equivalen todavía a ejecución de
planetaria/EAA/orbital desde la PWA con hardware.
