# Telesco-Pi 🔭

**Estación astronómica local para Linux x64 y ARM64, con interfaz mobile-first.**

---

## 📖 Descripción General

Telesco-Pi es una plataforma astronómica local para ordenadores **Linux x64**
y **Raspberry Pi 5 ARM64**. Integra sesiones, captura y dispositivos opcionales
desde una PWA, sin servicios externos durante la operación. La instalación
inicial requiere dependencias o un paquete offline de la arquitectura correcta.

## Instalación rápida — Linux

```bash
git clone https://github.com/dot-gabriel-ferrer/telesco-pi.git
cd telesco-pi
python3.11 install.py
~/.local/bin/telesco-pi serve
```

Abrir **http://127.0.0.1:8000**. La instalación comienza en simulación, no pide
root ni conecta hardware. Desde fuentes requiere Python 3.11–3.13, Node.js 20.19+ o 22.12+
y npm; un paquete de release incluye la UI y no requiere Node.js.
Consultar [instalación, actualización y rollback](docs/deployment/linux-installer.md).

La interfaz de usuario es una **Progressive Web App (PWA)** optimizada para dispositivos móviles, construida con React + TypeScript. El backend es una API REST/WebSocket robusta en Python con FastAPI.

### Estado real de la integración

El flujo conectar → sesión → preview → configurar → capturar → descargar funciona
en simulación y dispone de pruebas de API y navegador. Hay adaptadores opcionales
para **Player One Mars-M/Mars-C**, **EHD/Nncam (Photsat)** y control de ejes
**SkyWatcher por UDP**. El SDK oficial Player One **3.10.1** ya está obtenido,
con bibliotecas ARM64/x64 y descarga reproducible con SHA256 fijado.
Player One admite exposiciones individuales full-frame RAW8/RAW16 guardadas en
PNG; en color se conserva el mosaico Bayer y se hace demosaicing en el preview
de 8 bits. Sin vídeo planetario de alta velocidad todavía.

El control físico de SkyWatcher permite pasos relativos acotados y STOP; GoTo
absoluto, PARK y seguimiento altazimutal están bloqueados hasta validar referencia
y hardware. El movimiento real está además deshabilitado por defecto; STOP no
requiere habilitarlo. No se declara validación física completa. En este Linux
se detectó una Mars-C por USB; la apertura está bloqueada por permisos del
dispositivo. La montura no respondió a la consulta en la dirección prevista.
No se ejecutaron motores.

- [Plan mejorado y puertas de aceptación](docs/product/development-plan.md)
- [Integraciones, despliegue y configuración](docs/deployment/raspberry-pi.md)
- [Pruebas y limitaciones verificadas](docs/testing/device-integration.md)
- [Plan supervisado de pruebas físicas por agente](docs/testing/hardware-agent-plan.md)
- [Agente de validación de hardware](.github/agents/hardware-validation.agent.md)
- [Añadir cámaras/monturas y matriz de soporte](docs/architecture/adding-device-drivers.md)

---

## 🚀 Características Principales

Objetivos del producto; consultar el estado real anterior y el plan antes de
considerar operativas las funciones científicas avanzadas.

| Módulo | Descripción |
|---|---|
| **Control de montura** | Control en tiempo real de la montura SkyWatcher AZ-Go2 vía WiFi (protocolo SynScan) |
| **Captura de imagen** | Integración con la cámara Player One Mars M (USB 3.0) para captura planetaria y de alta velocidad |
| **Observación planetaria** | Modos dedicados para observación y captura de planetas, Luna y Sol |
| **EAA / Live Stacking** | Apilado en tiempo real (Electronically Assisted Astronomy) para observación de objetos de cielo profundo |
| **Seguimiento orbital** | Cálculo y seguimiento de satélites artificiales (ISS, etc.) y objetos en órbita terrestre |
| **Planificador de sesiones** | Herramienta de planificación de sesiones astronómicas con visibilidad de objetivos |
| **Diagnóstico** | Panel de diagnóstico del sistema (hardware, temperatura, conectividad) |
| **Offline-first** | Funciona completamente sin conexión a Internet una vez desplegado en la Raspberry Pi |

---

## 🛠️ Stack Tecnológico

### Backend
- **Python 3.11+** — Lenguaje principal del backend
- **FastAPI** — Framework web asíncrono de alto rendimiento (API REST + WebSockets)
- **Uvicorn** — Servidor ASGI de producción
- **PySerial** — Comunicación serial con dispositivos de hardware
- **SQLite** — Base de datos local embebida para persistencia de sesiones y configuración
- **WebSockets** — Streaming de datos en tiempo real hacia la PWA

### Frontend (PWA)
- **React 18** — Librería de interfaz de usuario
- **TypeScript** — Tipado estático para mayor robustez
- **Vite** — Bundler y servidor de desarrollo ultrarrápido
- **Tailwind CSS** — Framework CSS utility-first para diseño responsive y mobile-first
- **Service Workers** — Soporte offline y comportamiento de PWA instalable

### Infraestructura
- **Raspberry Pi 5** — Hardware de destino (ARM64)
- **systemd** — Gestión del servicio en producción
- **SQLite** — Almacenamiento local sin servidor de base de datos externo

---

## 📁 Estructura del Monorepo

```
telesco-pi/
├── apps/
│   ├── backend/          # Aplicación FastAPI (API REST + WebSockets)
│   └── frontend/         # PWA React + TypeScript + Vite
├── packages/
│   ├── shared-types/     # Tipos TypeScript compartidos entre frontend y SDK
│   └── sdk-client/       # Cliente SDK para consumir la API del backend
├── libs/
│   ├── config/           # Gestión de configuración del sistema
│   ├── devices/          # Drivers e interfaces de hardware (montura, cámara)
│   ├── storage/          # Capa de abstracción de base de datos (SQLite)
│   ├── sessions/         # Gestión de sesiones de observación
│   ├── diagnostics/      # Diagnóstico y monitoreo del sistema
│   └── astronomy/
│       ├── planner/      # Planificador de sesiones astronómicas
│       ├── processing/   # Procesado de imagen (stacking, calibración)
│       ├── orbital/      # Cálculo de órbitas y seguimiento de satélites
│       └── horizon/      # Cálculo de horizonte local y visibilidad
├── services/
│   ├── notifications/    # Servicio de notificaciones push
│   └── simulator/        # Simulador de hardware para desarrollo y pruebas
├── infra/
│   ├── scripts/          # Scripts de instalación y despliegue
│   ├── systemd/          # Unidades systemd para gestión de servicios
│   └── configs/          # Ficheros de configuración de entorno
├── tests/
│   ├── unit/             # Tests unitarios
│   ├── integration/      # Tests de integración
│   ├── e2e/              # Tests end-to-end
│   └── hardware/         # Tests de integración con hardware real
└── docs/
    ├── architecture/     # Diagramas y decisiones de arquitectura (ADRs)
    ├── api/              # Documentación de la API
    ├── product/          # Especificaciones de producto y user stories
    ├── testing/          # Estrategia y planes de pruebas
    ├── deployment/       # Guías de despliegue en Raspberry Pi
    ├── risks/            # Registro de riesgos técnicos
    └── ai_context/       # Prompts y contexto para los agentes de IA
```

---

## 🤖 Desarrollo Iterativo con Agentes de IA

Este proyecto se desarrolla de forma iterativa utilizando **agentes de IA especializados**:

| Agente | Responsabilidad |
|---|---|
| **Agente 1 — Backend** | Desarrollo del API FastAPI, drivers de hardware, lógica de negocio en Python |
| **Agente 2 — Frontend** | Desarrollo de la PWA React, componentes UI, integración con el SDK cliente |
| **Agente 3 — Astronomía** | Algoritmos astronómicos, cálculos orbitales, procesado de imagen, planificador |

Los prompts de sistema y el contexto de cada agente se encuentran en [`docs/ai_context/`](./docs/ai_context/).

---

## ⚙️ Instalación y Puesta en Marcha

> Las instrucciones de despliegue y acceso móvil están en
> [la guía Raspberry Pi](docs/deployment/raspberry-pi.md). La configuración
> predeterminada usa simulación y no conecta dispositivos automáticamente.

### Requisitos previos
- Raspberry Pi 5 con Raspberry Pi OS (64-bit) o similar
- Python 3.11–3.13
- Node.js 20+
- Montura SkyWatcher AZ-Go2 en la misma red WiFi
- Cámara Player One Mars M conectada por USB 3.0

### Inicio rápido (desarrollo local)

```bash
# Clonar el repositorio
git clone https://github.com/dot-gabriel-ferrer/telesco-pi.git
cd telesco-pi

# Backend, desde la raíz del repositorio
python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m uvicorn apps.backend.app.main:app --host 127.0.0.1 --port 8000

# Frontend, en otra terminal desde la raíz
cd apps/frontend
npm ci
npm run dev
```

Abrir `http://localhost:5173`. Desde Inicio, conectar montura y cámara simuladas,
iniciar una sesión y activar el preview. Captura permite ajustar exposición y
ganancia; Archivos permite descargar originales y PNG de previsualización.
El proxy Vite resuelve REST y WebSocket hacia el backend local.

### Validación

```bash
# Desde la raíz
.venv/bin/python -m pytest -q

cd apps/frontend
npm run build
npm run lint
npx playwright install chromium
# Detener antes los servidores manuales en 8000/5173.
# El runner arranca sus propios servidores y usa datos de prueba separados.
npm run test:e2e
```

### Referencias externas

- [Camera_Control_Photsat](https://github.com/dot-gabriel-ferrer/Camera_Control_Photsat):
  API Nncam externa, sin importar Qt ni redistribuir SDK/binarios.
- [skywatcher_open](https://github.com/skywatcher-pacific/skywatcher_open):
  referencia de protocolo; adaptador Python independiente.
- [awesome-ai-frontend](https://github.com/thestriver/awesome-ai-frontend):
  catálogo de inspiración, no una dependencia visual. La interfaz usa diseño
  propio, SVG y estilos locales, sin llamadas a servicios IA ni recursos remotos.

---

## 📄 Licencia

Copyright (c) 2026. Todos los derechos reservados.

Consulta el archivo [LICENSE](./LICENSE) para más detalles.
