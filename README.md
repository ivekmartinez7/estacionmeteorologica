---
título: IvekBot Weather Station — README
doc_id: DOC-001-01
versión: 1.3.0
estado: AS-IS
audiencia: humano
idioma: es-ES
verificado_en:
  commit: 1513c19
  fecha: 2026-08-14
  método: lectura_código
  archivos_clave:
    - app/main.py
    - app/agents/orchestrator.py
    - app/physics_engine.py
    - app/mcp_server.py
    - app/schemas.py
    - simulator/sensor_simulator.py
    - firmware/esp32_sensor_node.py
    - docker-compose.yml
    - .env.example
reglas:
  - "Nunca afirmar como AS-IS algo no verificado en archivos_clave."
  - "Todo bloque de código aquí es fragmento de contrato, no el fuente vigente."
prohibido:
  - "Citar umbrales físicos sin ruta de archivo."
  - "Usar '1 Hz', 'sub-segundo', '6 agentes' o 'License: MIT' como hecho."
---

# IvekBot Weather Station

Demo FastAPI de estación meteorológica para Xalapa: física determinista, dashboard por WebSocket, orquestador con gateway LLM opcional y telemetría simulada en memoria.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)

No hay archivo `LICENSE` en el repo. Este proyecto **no es Django** (la carpeta padre se llama `django/`; el runtime es FastAPI 3.5.0).

## Qué hace hoy (AS-IS)

- **Física determinista** en `compute_atmospheric_physics()` (`app/physics_engine.py:50`): rocío Magnus-Tetens / MetPy opcional, LCL Espy-Bolton, CAPE/CIN/PWAT/LI **heurísticos** (no sounding), Norte por umbrales absolutos.
- **Un orquestador** `WeatherOrchestrator.execute_pipeline()` (`app/agents/orchestrator.py:162`): física → riesgo → ensamble 14d **sintético** → resumen + boletín (LLM o plantilla).
- **4 tools FastMCP** en `app/mcp_server.py`: `ingest_and_validate_telemetry`, `calculate_thermodynamics`, `assess_basin_hydrology_risk`, `query_graphify_knowledge`.
- **Dashboard** en `static/` servido en `/`. WebSocket `/ws/telemetry/live` emite cada **2 s** (`app/main.py:107`).
- **Simulador** `simulator/sensor_simulator.py` hace POST a `/api/v1/telemetry/ingest` cada **3 s**.
- **LLM opcional**: endpoint OpenAI-compatible. Sin `LLM_API_KEY` (o con el placeholder) hay fallback de plantillas; el pipeline no se corta.

## Qué no está integrado hoy

- Persistencia: `docker-compose.yml` define TimescaleDB, Redis y Mosquitto; `app/` **no** escribe ni lee esos servicios. El estado vive en `current_telemetry` + `history_buffer`.
- Clases de agente SA1–SA6, pysteps, LightGBM, GOES-16, Kalman, difusión real a WhatsApp/Telegram/X.
- Stream a 1 Hz. Firmware ESP32 con BME280 real (el payload térmico de `firmware/esp32_sensor_node.py:73-81` es **fijo**).
- Licencia MIT.

Detalle de diseño y TO-BE: [SDD.md](SDD.md). Fórmulas regionales de Xalapa: [estacion_meteorologica.md](estacion_meteorologica.md). Grafo generado (no es spec): [graphify-out/GRAPH_REPORT.md](graphify-out/GRAPH_REPORT.md).

## Estado de implementación

| Componente | Archivo real | Status | Evidencia |
|---|---|---|---|
| Pipeline de pronóstico | `app/agents/orchestrator.py` | AS-IS | `:162` `execute_pipeline()` |
| Física determinista | `app/physics_engine.py` | AS-IS | `:50` heurística + MetPy opcional |
| Riesgo por cuenca | `app/mcp_server.py` | AS-IS | `:36` umbrales `:52/:60/:70/:80` |
| Stream dashboard | `app/main.py` | AS-IS | `:107` `asyncio.sleep(2)` |
| Simulador HTTP | `simulator/sensor_simulator.py` | AS-IS | `:10` POST ingest; `:48` `sleep(3)` |
| Gateway LLM + fallback | `app/agents/orchestrator.py` | AS-IS | `:96` `_call_llm`; `:224` plantillas |
| TimescaleDB / Redis / MQTT | `docker-compose.yml` | TO-BE integración | servicios definidos; app no los usa |
| Roles SA1–SA6 | — | TO-BE | no existen como clases |

## Inicio rápido

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

En otra terminal:

```bash
pip install requests
python simulator/sensor_simulator.py
```

Abre **http://localhost:8000**

`python-dotenv` está en `requirements.txt`. `WeatherOrchestrator` llama `load_dotenv()` (`app/agents/orchestrator.py:9-12`). Sin esa dependencia, `cp .env.example .env` no surte efecto.

### Docker Compose

```bash
docker compose up -d --build
```

Levanta app + TimescaleDB + Redis + Mosquitto. Inyecta `.env` vía `env_file`. La app **sigue en memoria**: los tres sidecars no se consumen desde `app/`.

## Endpoints reales (`app/main.py`)

| Ruta | Método | Función |
|---|---|---|
| `/` | GET | Dashboard `static/index.html` |
| `/ws/telemetry/live` | WebSocket | Pulso cada 2 s (`telemetry` + `thermodynamics`) |
| `/api/v1/dashboard/overview` | GET | `DashboardOverview` vía `execute_pipeline` |
| `/api/v1/forecast/report` | GET | `ForecastReport` |
| `/api/v1/telemetry/ingest` | POST | Actualiza estado en memoria y rebroadcast |
| `/api/v1/knowledge/query` | POST | `query_graphify_knowledge` (CLI Graphify) |
| `/static/*` | GET | Assets del dashboard |

No existen `/api/v1/telemetry/history`, `/thermodynamics/sounding`, `/radar/frames` ni `/alerts/publish`.

## LLM (variables que sí se leen)

| Variable | Default | Efecto |
|---|---|---|
| `LLM_BASE_URL` | `https://api.openai.com/v1` | `{base}/chat/completions` |
| `LLM_API_KEY` | vacío | vacío o `tu_api_key_aqui` → fallback |
| `ORCHESTRATOR_MODEL` | `gpt-4o-mini` | resumen ejecutivo |
| `RISK_AGENT_MODEL` | = orquestador | boletín |
| `ORCHESTRATOR_MAX_TOKENS` | `250` | techo del resumen |
| `RISK_AGENT_MAX_TOKENS` | `300` | techo del boletín |
| `ORCHESTRATOR_TEMPERATURE` / `RISK_AGENT_TEMPERATURE` | `0.3` | temperatura |
| `LLM_ENABLE_PROMPT_CACHE` | `1` | `cache_control` en system |
| `LLM_CACHE_TTL` | `60` | dedup local; `0` lo apaga |

`LLM_PROVIDER`, `DATABASE_URL`, `REDIS_URL`, `MQTT_*`, `GRAPHIFY_TOKEN_BUDGET`, `ENVIRONMENT`/`PORT`/`HOST` están en `.env.example` y **no** las consume `app/` hoy.

El LLM **solo** puede redactar `executive_summary` y `public_bulletin`. CAPE, alerta, ensamble y schemas son deterministas.

### Ejemplo OpenRouter

```env
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=tu_api_key
ORCHESTRATOR_MODEL=deepseek/deepseek-r1
RISK_AGENT_MODEL=qwen/qwen-2.5-72b-instruct
```

### Ejemplo Ollama local

```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
ORCHESTRATOR_MODEL=qwen2.5:14b
RISK_AGENT_MODEL=qwen2.5:7b
```

## Firmware y simulador

- `simulator/sensor_simulator.py` — fuente de datos de la demo HTTP.
- `firmware/esp32_sensor_node.py` — MicroPython + MQTT QoS 1. Temp/humedad/presión fijas; lluvia por IRQ; batería por ADC. La app **no** consume MQTT.

## Cómo leer los docs

| Pregunta | Documento |
|---|---|
| ¿Cómo lo corro hoy? | este README |
| ¿Qué hay vs qué se quiere? | [SDD.md](SDD.md) |
| ¿Por qué esos umbrales en Xalapa? | [estacion_meteorologica.md](estacion_meteorologica.md) |
| ¿Qué símbolos conecta el repo? | [graphify-out/GRAPH_REPORT.md](graphify-out/GRAPH_REPORT.md) (artefacto 2026-08-14; `THEME` aislado = constante JS en `static/js/dashboard.js:9`) |

## Checklist corto

- [x] Front-matter con commit `1513c19`.
- [x] Quick start: uvicorn + simulador + URL.
- [x] Sin badge MIT. Sin “1 Hz” AS-IS. Sin SA1–SA6 como clases.
- [x] Infra Docker ≠ integración.
