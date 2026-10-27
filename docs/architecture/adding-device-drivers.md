# Añadir cámaras y monturas

La distribución Linux incluye el mismo backend en x64 y ARM64. Los SDK
nativos se cargan al conectar, nunca al importar/iniciar; que el paquete se
instale en una arquitectura no certifica el hardware.

## Contrato de extensión

1. Implementar `CameraDriver` o `MountDriver` de `libs/devices/interfaces.py`
   en un módulo propio. No introducir UI del fabricante ni importar binarios
   de otros repositorios sin licencia/arquitectura verificadas.
2. Devolver `DeviceStatus` con implementación real, capacidades **que sí se
   implementan**, límites, estado y metadatos de identidad/readback. Las
   operaciones no soportadas se rechazan explícitamente, no retornan éxito.
3. La cámara produce `CapturedFrame` con dimensiones, payload sin pérdida y
   metadatos de sensor/formato. `imaging.preview_png` solo transforma la copia
   de presentación: conservar original, profundidad y patrón Bayer. Una
   extensión a otro formato requiere pruebas de decodificación/exportación.
4. Registrar el nombre tipado en Settings y la factory correspondiente en
   `DeviceService.start`; añadirlo también a `telesco-pi configure` y al
   ejemplo de entorno. Mantener separación entre `simulator`, `stub` y
   `configured`. Un fallo real **nunca** selecciona el simulador.
5. Serializar acceso nativo, acotar timeouts y cerrar recursos tras fallo.
   La cancelación async no debe liberar un dispositivo mientras un hilo
   nativo sigue usándolo. Probar apertura parcial, timeout y cierre fallido.
6. Monturas: consultas sin movimiento al conectar, STOP disponible,
   movimiento deshabilitado por defecto, límites verificados, ningún reintento
   automático de comandos motores. Calibración/GoTo/seguimiento nuevos necesitan
   diseño separado, límites y supervisión física; no basta añadir botones.
7. Añadir fake SDK o controlador local para pruebas de protocolo, unidades,
   rangos, errores, selección/serial, buffers, API y ausencia de fallback.
   SDK opcional nunca es requisito para arrancar simulación o instalar.
8. Documentar descarga/versiones/licencia, ABI x64/ARM64, permisos mínimos,
   hardware/firmware realmente ensayados y casos pendientes. Extender el
   banco opt-in y el informe con identificación del modelo exacto.

No se cargan automáticamente plugins arbitrarios desde la red ni por nombre
en un archivo remoto. Para esta versión los drivers se revisan y registran en
el código de la distribución; simplifica compatibilidad, pruebas y límites.
Un protocolo público de plugins se diseñará cuando haya una segunda familia
implementada que lo necesite, no como abstracción especulativa.

## Matriz de soporte actual

| Driver | Software | Verificación física |
| --- | --- | --- |
| Simuladores cámara/montura | Flujo completo y E2E; patrón sintético identificado | No aplica |
| Player One Mars-M | RAW8/RAW16, full-frame bin1, control manual, preview mono | Pendiente |
| Player One Mars-C | RAW8/RAW16 Bayer preservado, preview color/demosaicing | USB a0a0:4620 detectado en Linux x64; apertura bloqueada por permisos |
| Nncam | RAW8 mono y controles básicos mediante SDK externo | Pendiente |
| SkyWatcher UDP | Handshake, pasos finitos <=0.25°/s, STOP, bloqueo de movimiento | Consulta a dirección prevista sin respuesta; pendiente red/equipo |

El identificador USB es evidencia de enumeración del sistema, no demuestra
modelo reportado por SDK ni adquisición correcta. No se declaran compatibles
todas las cámaras Player One porque compartan SDK, ni todas las monturas
SkyWatcher porque compartan partes del protocolo.
