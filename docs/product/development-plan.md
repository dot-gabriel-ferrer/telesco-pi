# Plan de desarrollo e integración

Este plan concreta el [roadmap original](../ai_context/anexo_comun_1_arquitectura.txt)
y sus [criterios de aceptación](../ai_context/anexo_comun_2_criterios.txt).
No reemplaza las fases científicas ni convierte pruebas simuladas en validación física.

## Entrega Linux 0.2.0

El desarrollo y la validación de software se realizan en este **Linux x64**,
sin depender de una Raspberry conectada. La misma distribución soporta Linux
ARM64, pendiente de ejecutar físicamente allí. Se entrega
[instalador de usuario, paquete y rollback](../deployment/linux-installer.md),
PWA y API en un solo origen, constraints de dependencias y CI del instalador.

- [x] Distribución con UI/catálogos, CLI y configuración persistente separada.
- [x] Instalar sin root; no habilitar servicios ni abrir hardware automáticamente.
- [x] Mars-M y Mars-C con RAW Bayer preservado y preview color probado con datos sintéticos.
- [x] Pruebas de instalación limpia, actualización y rollback con datos conservados.
- [ ] Abrir/capturar cámara local: dispositivo Mars-C a0a0:4620 sin permiso RW.
- [ ] Montura real: consulta de firmware a la dirección prevista sin respuesta.
- [ ] ARM64, motores, Pixel/TLS y sesión física prolongada: no certificados.

No se elimina la licencia propietaria existente ni se redistribuye el SDK.
Las futuras familias de hardware siguen
[el contrato de extensión](../architecture/adding-device-drivers.md).

### Ampliación 0.2.1: procesado operativo de originales

- [x] Pipeline planetario conectado a API y biblioteca PWA: selección de
  originales, calidad empírica, alineación por traslación, apilado y realce.
- [x] Exportar PNG16/NPY y preview indexados con procedencia y originales intactos.
- [x] Validación de sesión/identidad/formato, memoria, errores y concurrencia.
- [x] Pruebas API, navegador y smoke de paquete instalado.
- [ ] Vídeo/series de alta velocidad, EAA continuo y solve calibrado: pendientes
  de implementación especializada y aceptación física; no equivalen a procesar
  un conjunto acotado de imágenes almacenadas.

## Fuentes y decisiones

| Fuente | Uso | Límite |
| --- | --- | --- |
| [SDK oficial Player One](https://player-one-astronomy.com/service/software/) | Adaptador propio ctypes para Mars-M, SDK Linux 3.10.1 ARM64/x64 externo, RAW8/RAW16 PNG | Obtenido y cargado en x64; ARM64/cámara todavía sin validación física. No es el SDK Nncam. |
| [Camera_Control_Photsat](https://github.com/dot-gabriel-ferrer/Camera_Control_Photsat) | Adaptador Python al SDK Nncam que utiliza Photsat, sin interfaz Qt | Es para EHD/Nncam; no prueba compatibilidad con Player One Mars M. SDK externo, binario ARM64 y permisos de uso necesarios. |
| [skywatcher_open](https://github.com/skywatcher-pacific/skywatcher_open) | Referencia del protocolo de los controladores de ejes; implementación Python independiente y transporte UDP | Los ejemplos seriales/C# no certifican AZ-Go2 por WiFi. Validar firmware, dirección y sentido de ejes en banco. |
| [awesome-ai-frontend](https://github.com/thestriver/awesome-ai-frontend) | Catálogo de inspiración y recursos de frontend | No es un kit visual instalable. Diseño propio, sin APIs externas, imágenes remotas ni dependencia de IA en campo. |

Los repositorios de hardware no declaran una licencia general en GitHub.
No se incorporan sus fuentes ni sus binarios. El operador debe obtener e instalar
el SDK autorizado de su proveedor. Nunca se sustituye hardware fallido por simulación.

Revisiones consultadas:
[Photsat `095dbb1`](https://github.com/dot-gabriel-ferrer/Camera_Control_Photsat/commit/095dbb165ceb22c465a24de0f1d91508aadc122c),
[SkyWatcher `5c8277c`](https://github.com/skywatcher-pacific/skywatcher_open/commit/5c8277c7c34aa4be870202ecbb56bbed29223650) y
[Frontend `2dea4e2`](https://github.com/thestriver/awesome-ai-frontend/commit/2dea4e2a8b030de7ebbff6ab8a41050d09fdbb3f).

## Iteración ejecutable: operación local de dispositivos

1. **Contratos y configuración**
   - Selección explícita de simulación, stubs o adaptadores independientes.
   - Validar puerto, tiempo de espera, límites de desplazamiento y cámara.
   - Mantener la simulación como valor predeterminado.
2. **Adaptadores**
   - Nncam: enumeración, apertura, exposición/ganancia, captura y cierre.
   - Player One Mars-M: SDK oficial fijado, selección por serial, controles
     manuales con readback y PNG RAW8/RAW16; preview 8 bits.
   - SkyWatcher: consulta de controladora, desplazamiento relativo acotado y STOP
     en ambos ejes; timeout sin reintentar órdenes de movimiento.
   - No habilitar GoTo absoluto, PARK ni seguimiento altazimutal sin modelo de
     referencia/calibración. Rechazo explícito y capacidades honestas.
3. **Flujo API completo**
   - Conectar, configurar, previsualizar sin escribir frames al disco y capturar
     en una sesión persistente.
   - Errores estructurados, nombres de captura seguros y únicos; archivos
     descargables por identificador.
4. **Interfaz de observación**
   - Panel dark-first propio, responsive, modo rojo, foco visible, movimiento
     reducido, estados de hardware y simulación inequívocos.
   - Acciones con resultado/error visible, conexión de dispositivos, preview,
     exposición/ganancia y archivos de la sesión.
5. **Entrega reproducible**
   - Pruebas de protocolo, SDK falso y API/simulador; build y lint del frontend.
   - Prueba de flujo móvil y escritorio en navegador.
   - Configuración y servicio systemd documentados; no iniciar motores ni instalar
     servicios automáticamente en el equipo de desarrollo.

## Puertas de aceptación de hardware (no ejecutables sin equipo)

El procedimiento ejecutable por IA, autorizaciones, orden de fases, umbrales,
evidencias y recuperación están definidos en
[el plan de banco](../testing/hardware-agent-plan.md).
Usar manualmente [el agente de validación](../../.github/agents/hardware-validation.agent.md);
no autoriza movimiento por sí solo ni permite operación desatendida.

- [x] Obtener SDK oficial Player One 3.10.1, fijar SHA256 y verificar carga x64.
- [x] Implementar adaptador Mars-M y pruebas de ABI/SDK falso/API.
- [x] Preparar plan, plantilla de entorno y agente de pruebas físicas.
- [ ] Confirmar serial/modelo exacto de la Mars-M conectada a la Pi.
- [ ] Verificar carga ARM64 y permisos USB en la Raspberry.
- [ ] Banco AZ-Go2: confirmar respuesta UDP, unidades, sentido de cada eje,
      pasos de 0.1 grados autorizados, STOP y recuperación segura.
- [ ] Medir captura/preview, temperatura, CPU, memoria y almacenamiento en Pi 5.
- [ ] Verificar PWA en Pixel, tethering/WiFi y HTTPS para instalación/offline.
- [ ] Sesión prolongada, desconexión USB/WiFi y reinicio con restauración.

No se declara V1 física terminada hasta superar estas puertas.

## Continuidad del roadmap científico

Las fases 3 a 8 originales conservan su prioridad: catálogos/planner, calibración
y solve local, planetaria, EAA, orbital y robustez. El repositorio contiene
bibliotecas científicas y pruebas, pero su integración operacional completa
debe verificarse por separado: no basta con mostrar botones o endpoints stub.
El seguimiento orbital y el seguimiento sidéreo altazimutal necesitan un lazo
de control calibrado, límites mecánicos y validación física antes de habilitarse.
La máscara IA continúa en V1.5 experimental.

El resultado y las pruebas de esta iteración se registran en
[la guía de validación](../testing/device-integration.md).

## Seguimiento de esta entrega

- [x] Contratos y selección explícita de drivers.
- [x] Adaptador Nncam externo y controlador SkyWatcher relativo, con pruebas.
- [x] Flujo sesión/preview/captura/descarga y errores explícitos.
- [x] Interfaz responsive, modo rojo y controles operativos.
- [x] Pruebas reproducibles, CI y plantillas de despliegue.
- [x] SDK Player One obtenido, adaptador RAW16 y protocolo supervisado por IA.
- [ ] Certificación física y fases avanzadas: pendientes, sin
      presentarlas como funcionalidades terminadas.

La prueba de navegador detectó que el planificador existente construía su
contrato sin `request_id` ni `session_id`. Se corrigió el flujo para utilizar una
sesión real activa y el contexto de petición; la UI exige iniciar sesión y
muestra el error cuando no es posible generar el plan.
