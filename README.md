# ⚡ IvekBot Weather Station — Estación Meteorológica Digital Multi-Agente

> **Ecosistema Meteorológico Digital Autónomo con Inteligencia Artificial, Física Atmosférica Determinista (MetPy), GraphRAG (Graphify), LLM Gateway Agnóstico y Dashboard en Tiempo Real.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![FastMCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io)
[![Graphify](https://img.shields.io/badge/GraphRAG-Graphify-orange.svg)](https://github.com/safishamsi/graphify)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Descripción del Proyecto

**IvekBot Weather Station** es una plataforma meteorológica modular y escalable que combina:

1. **🔬 Núcleo Físico Determinista (`MetPy`):** Cálculos rigurosos de termodinámica atmosférica ($CAPE$, $CIN$, $PWAT$, $LCL$, $LFC$, detección de *Nortes*) a coste **$0 de tokens**.
2. **🤖 Orquestación Multi-Agente (FastMCP):** 6 subagentes especializados y un orquestador master coordinados bajo el protocolo estándar MCP.
3. **🔌 LLM Gateway Agnóstico (Configurable por el Usuario):** Conecta cualquier modelo comercial (OpenAI, Gemini, Anthropic, DeepSeek, Groq, OpenRouter, Mistral), servicios de planes por tokens, o servidores de inferencia local (Ollama, vLLM, LM Studio) mediante endpoints compatibles con OpenAI (`/v1/chat/completions`).
4. **🧠 Memoria Estructurada GraphRAG (`Graphify`):** Grafo de conocimiento navegable con detección de comunidades (Louvain) que reduce drásticamente el consumo de tokens (`--budget 1500`).
5. **⚡ Dashboard Reactivo en Tiempo Real:** Transmisión continua sub-segundo vía WebSockets (`/ws/telemetry/live`) con gráficas dinámicas de Apache ECharts y abanicos de probabilidad a 14 días ($p_{10}, p_{50}, p_{90}$).
6. **📡 Telemetría IoT Resiliente (ESP32):** Firmware MicroPython con soporte MQTT QoS 1 y control de calidad (QC) con filtros anti-ruido (*Modified Z-Score*).
7. **🗄️ Persistencia con TimescaleDB:** Almacenamiento optimizado de series de tiempo mediante *hypertables* particionadas y vistas materializadas continuas cada 5 minutos.

---

## ⚙️ Configuración de tu Proveedor de LLM Preferido

Copia el archivo de ejemplo `.env.example` a `.env`:
```bash
cp .env.example .env
```

Configura en tu `.env` las credenciales y el modelo de tu elección:

### Ejemplo 1: Con OpenAI / OpenRouter / DeepSeek / Groq
```env
LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=tu_api_key_de_openrouter

ORCHESTRATOR_MODEL=deepseek/deepseek-r1
RISK_AGENT_MODEL=qwen/qwen-2.5-72b-instruct
```

### Ejemplo 2: Con Inferencia Local (Ollama / vLLM - 100% Gratis y Privado)
```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama

ORCHESTRATOR_MODEL=qwen2.5:14b
RISK_AGENT_MODEL=qwen2.5:7b
```

> **Nota:** Si no configuras ninguna API Key, el sistema continúa funcionando al 100% en tiempo real utilizando sus motores deterministas y plantillas meteorológicas de respaldo sin fallar.

---

## 🚀 Inicio Rápido

### 1. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 2. Ejecutar el Servidor FastAPI & Dashboard
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Abre tu navegador en: **`http://localhost:8000`**

### 3. Ejecución con Docker Compose
```bash
docker compose up -d --build
```

---

## 📄 Documentación Técnica Completa

- Consulta el **[SDD.md (Software Design Document)](SDD.md)** para la especificación formal de ingeniería de software.
- Consulta **[estacion_meteorologica.md](estacion_meteorologica.md)** para la memoria técnica y fórmulas atmosféricas.
