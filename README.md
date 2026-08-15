# ⚡ IvekBot Weather Station — Estación Meteorológica Digital Multi-Agente

> **Ecosistema Meteorológico Digital con Física Atmosférica Determinista (MetPy), GraphRAG (Graphify), LLM Gateway Agnóstico y Dashboard en Tiempo Real.**
> **Estado actual: AS-IS en memoria (demo funcional). Persistencia TimescaleDB/Redis/MQTT y subagentes SA1-SA6 son TO-BE — ver SDD §2 y AUDITORIA_GAPS_DOCUMENTACION.md.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![FastMCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io)
[![Graphify](https://img.shields.io/badge/GraphRAG-Graphify-orange.svg)](https://github.com/safishamsi/graphify)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Descripción del Proyecto

**IvekBot Weather Station** es una plataforma meteorológica modular que combina:

1. **🔬 Núcleo Físico Determinista (`MetPy`):** Cálculos de termodinámica atmosférica (CAPE, CIN, PWAT, LCL, LFC, detección de *Nortes*) con fallback heurístico si MetPy no está; coste **$0 de tokens** en operación baseline.
2. **🤖 Orquestación (FastMCP):** 1 orquestador central `WeatherOrchestrator` + 4 tools FastMCP (`ingest_and_validate_telemetry`, `calculate_thermodynamics`, `assess_basin_hydrology_risk`, `query_graphify_knowledge`). Arquitectura conceptual prevé 6 subagentes especializados SA1-SA6 — ver SDD §4 (TO-BE).
3. **🔌 LLM Gateway Agnóstico (Configurable por el Usuario):** Cualquier endpoint OpenAI-compatible (`/v1/chat/completions`): OpenAI, Gemini, Anthropic, DeepSeek, Groq, OpenRouter, Mistral, u Ollama/vLLM/LM Studio local.
4. **🧠 Memoria Estructurada GraphRAG (`Graphify`):** Grafo navegable con comunidades Louvain; consultas con presupuesto fijo (`--budget 1500`, default). Solo `query_graphify_knowledge` está cableado; `find_path`/`explain` son TO-BE.
5. **⚡ Dashboard Reactivo en Tiempo Real:** WebSocket `/ws/telemetry/live` emite cada **2 s (0.5 Hz)** + 5 tarjetas métricas, gauge CAPE 0-3500, serie 24h ECharts y abanico 14 días **sintético** (`p10/p50/p90` pseudoaleatorios; frontend grafica `p50/p90`). Multi-modelo real es TO-BE.
6. **📡 Telemetría IoT (ESP32):** Firmware MicroPython publica MQTT **QoS 1**; QC actual es validación simple (`temp>45` o `hum>100` → `qc.is_valid=false`). `Modified Z-Score` / AKF son TO-BE (ver SDD §4.2).
7. **🗄️ Persistencia (TimescaleDB):** `sensor_telemetry` como hypertable sí existe en `database/init.sql`; la vista continua `telemetry_5min` es TO-BE (solo en docs, no en SQL). El SQL real también crea `forecast_verification_log` y `weather_alerts` (no documentadas). **AS-IS el app corre 100% en memoria** — DB/Redis/MQTT no se consumen (ver auditoría).

---

## ⚙️ Configuración de tu Proveedor de LLM Preferido

> **Requisito:** instala `python-dotenv` (ya en `requirements.txt`) para que `.env` surta efecto. Sin él, `os.getenv` no lee el archivo.

```bash
cp .env.example .env
# edita .env con tu API key / base_url / modelos
pip install -r requirements.txt
```

### Variables que SÍ tienen efecto hoy (orquestador lee 6)

| Variable | Default | Efecto |
|---|---|---|
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Endpoint `/chat/completions` |
| `LLM_API_KEY` | *(vacío)* | Si vacío o `tu_api_key_aqui` → fallback determinista, sin fallo |
| `ORCHESTRATOR_MODEL` | `gpt-4o-mini` | Modelo para resumen ejecutivo |
| `RISK_AGENT_MODEL` | `=ORCHESTRATOR_MODEL` | Modelo para boletín ciudadano |
| `ORCHESTRATOR_MAX_TOKENS` | `250` | Límite resumen (si no está → 250) |
| `ORCHESTRATOR_TEMPERATURE` / `RISK_AGENT_*` | `0.3` | Temperatura LLM (si no está → 0.3) |

`LLM_PROVIDER`, `DATABASE_URL`, `REDIS_URL`, `MQTT_*`, `GRAPHIFY_TOKEN_BUDGET`, `ENVIRONMENT/PORT/HOST` están en `.env.example` como **TO-BE** (documentadas, aún no cableadas).

### Ejemplo 1: OpenAI / OpenRouter / DeepSeek / Groq

```env
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=tu_api_key_de_openrouter
ORCHESTRATOR_MODEL=deepseek/deepseek-r1
RISK_AGENT_MODEL=qwen/qwen-2.5-72b-instruct
```

### Ejemplo 2: Inferencia Local (Ollama / vLLM — 100% Gratis y Privado)

```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
ORCHESTRATOR_MODEL=qwen2.5:14b
RISK_AGENT_MODEL=qwen2.5:7b
```

> Sin API key el sistema sigue **100% en tiempo real** con motores deterministas + plantillas (ver `orchestrator.py:125-161`).

---

## 🚀 Inicio Rápido

### 1. Instalación

```bash
pip install -r requirements.txt
# simulador necesita requests (opcional, no bloquea el API si falta)
```

### 2. Servidor FastAPI + Dashboard

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# http://localhost:8000  → sirve static/index.html
```

Endpoints reales: `GET /api/v1/dashboard/overview`, `GET /api/v1/forecast/report`, `POST /api/v1/telemetry/ingest`, `POST /api/v1/knowledge/query`, `WS /ws/telemetry/live`, `GET /`, `GET /static/*`.

### 3. Docker Compose

```bash
docker compose up -d --build
# Requiere .env con LLM_* si quieres LLM dentro del contenedor (ver docker-compose.yml)
```

---

## 📄 Documentación Técnica Completa

- **[SDD.md](SDD.md)** — spec formal (IEEE 1016). Secciones marcadas AS-IS vs TO-BE tras auditoría.
- **[estacion_meteorologica.md](estacion_meteorologica.md)** — ⚠️ **HISTÓRICO/DESFASADO** (dump ~85% duplicado). Mantener solo como archivo histórico; no usar para implementar. Ver auditoría.
- **[AUDITORIA_GAPS_DOCUMENTACION.md](AUDITORIA_GAPS_DOCUMENTACION.md)** — auditoría claim↔código del 2026-08-14 (research-lead).

## 🔍 Limitaciones conocidas (honest mode)

- Ensamble 14d sintético, sin difusión real, sin Kalman/pysteps/LightGBM/GOES-16/CAMS.
- Sin `/health`, sin `tests/`, sin CI, logging no estructurado; healthchecks solo en `timescaledb`/`redis`.
- Niebla orográfica (`T-Td<=0.8`, `LCL<=1450`) y convección severa (`CAPE>=1800`…) solo en memoria técnica, no en `physics_engine.py`.
