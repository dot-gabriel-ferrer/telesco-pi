# Telesco-Pi 🔭

**Plataforma astronómica avanzada y mobile-first para Raspberry Pi 5.**

---

## 📖 Descripción General

Telesco-Pi es una plataforma astronómica local (actualmente privada) diseñada para ejecutarse sobre una **Raspberry Pi 5**. Proporciona control completo de una montura **SkyWatcher AZ-Go2 WiFi** y una cámara **Player One Mars M USB 3.0**, todo desde un smartphone en campo, sin conexión a Internet (modo *offline-first*).

La interfaz de usuario es una **Progressive Web App (PWA)** optimizada para dispositivos móviles, construida con React + TypeScript. El backend es una API REST/WebSocket robusta en Python con FastAPI.

---

## 🚀 Características Principales

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

> **Nota:** Las instrucciones detalladas de instalación y despliegue en Raspberry Pi 5 se documentarán en [`docs/deployment/`](./docs/deployment/) conforme avance el desarrollo.

### Requisitos previos
- Raspberry Pi 5 con Raspberry Pi OS (64-bit) o similar
- Python 3.11+
- Node.js 20+
- Montura SkyWatcher AZ-Go2 en la misma red WiFi
- Cámara Player One Mars M conectada por USB 3.0

### Inicio rápido (desarrollo local)

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd telesco-pi

# Backend
cd apps/backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (en otra terminal)
cd apps/frontend
npm install
npm run dev
```

---

## 📄 Licencia

Copyright (c) 2026. Todos los derechos reservados.

Consulta el archivo [LICENSE](./LICENSE) para más detalles.
