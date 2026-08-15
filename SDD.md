# Software Design Document (SDD)
## Documento de Diseño de Software: Estación Meteorológica Digital Multi-Agente (*IvekBot Weather Station*)

- **Document ID:** SDD-IVEKBOT-WX-2026-V1
- **Versión:** 1.2.0 (Corrección post-auditoría 2026-08-14 · IEEE 1016 + AS-IS vs TO-BE)
- **Fecha:** 2026-08-14
- **Estándar:** IEEE 1016-2009 (Software Design Descriptions), FastMCP, Pydantic v2, TimescaleDB, Docker
- **Ubicación Geográfica de Referencia:** Xalapa, Veracruz, México ($19.54^\\circ\\text{N},\\, 96.92^\\circ\\text{W}$, Altitud: $1,420\\,\\text{msnm}$)
- **Estado del documento:** Tras auditoría `AUDITORIA_GAPS_DOCUMENTACION.md` (2026-08-14). Todo lo marcado **[AS-IS]** está implementado y verificado en código; **[TO-BE]** es spec/roadmap aún no cableado. Ver README para resumen ejecutivo.


---

## 1. Introducción y Filosofía del Sistema

### 1.1. Objetivo General
Diseñar y construir un ecosistema meteorológico digital autónomo, de alta disponibilidad, modular y con capacidad de razonamiento cognitivo. El sistema supera a las estaciones tradicionales combinando **telemetría física de superficie**, **motores deterministas de física atmosférica**, **modelos numéricos y neuronales globales (NWP / AI-NWP)**, **orquestación multi-agente vía FastMCP**, **GraphRAG con Graphify** y un **Dashboard reactivo en tiempo real**.

### 1.2. Principios Rectores de Diseño
1. **Separación Estricta entre Lógica Determinista y Razonamiento Cognitivo:**
   - Todo cálculo matemático, termodinámico y de extrapolación de sensores se ejecuta en Python puro / C++ sin intervención de LLMs, garantizando **cero alucinaciones** y **coste $0$ de tokens** en la operación continua baseline.
   - Los Modelos de Lenguaje (LLMs) se activan de forma quirúrgica únicamente para interpretar escenarios complejos, evaluar riesgos por cuenca, consultar el grafo de conocimiento y redactar boletines de Protección Civil.
2. **Pasarela de LLMs Agnóstica al Proveedor (*Provider-Agnostic LLM Gateway*):**
   - El sistema no ata al usuario a ningún modelo propietario específico. Soporta cualquier proveedor comercial mediante API key (OpenAI, Anthropic, Google Gemini, DeepSeek, Groq, OpenRouter, Mistral), servicios de planes por tokens, o servidores de inferencia locales (Ollama, vLLM, LM Studio) usando el estándar OpenAI-Compatible API (`/v1/chat/completions`).
3. **Eficiencia Extrema de Tokens (GraphRAG con Graphify):**
   - La base de conocimiento sobre el código, reglas sinópticas y manuales de Protección Civil se indexa en un grafo con comunidades de Louvain, permitiendo consultas contextuales con un presupuesto estricto (`--budget 1500`).
4. **Resiliencia Operativa y Degradación Elegante (*Graceful Degradation*):**
   - Si no se configura ninguna API key de LLM o se agotan los tokens, el sistema conmuta automáticamente a sus motores deterministas basados en plantillas físicas sin interrumpir la operación ni el Dashboard.

---

## 2. Arquitectura General y Separación de Fases

### 2.1. Desacoplamiento: Desarrollo vs. Operación (Runtime)

> **[AS-IS]** hoy el runtime es **en memoria** (FastAPI + WebSocket 0.5 Hz + orquestador + 4 tools). **[TO-BE]** prevé MQTT/Redis/TimescaleDB/pysteps/LightGBM/GOES. Ver auditoría.

```
+---------------------------------------------------------------------------------------------------------------+
| FASE              | ACTORES / HERRAMIENTAS              | RESPONSABILIDAD TÉCNICA                             |
+-------------------+-------------------------------------+-----------------------------------------------------+
| DESARROLLO        | Desarrollador + LLM de su elección  | Construcción de código, definición de esquemas,     |
| (Build-Time)      | (vía API o Local)                   | entrenamiento de modelos ML y compilación Graphify. |
+-------------------+-------------------------------------+-----------------------------------------------------+
| OPERACIÓN [AS-IS] | WeatherOrchestrator + 4 tools FastMCP | Telemetría en memoria, física MetPy, ensamble       |
|                   | + FastAPI + WebSocket 0.5 Hz (2 s)  | sintético 14d, síntesis LLM con fallback.           |
| OPERACIÓN [TO-BE] | 6 Subagentes SA1-SA6 + MQTT 1 Hz    | Ingesta MQTT real, pysteps radar, super-ensamble ML,|
|                   | + TimescaleDB + Redis + GOES/LightGBM| verif. CRPS/EMA y alertas multicanal.               |
+---------------------------------------------------------------------------------------------------------------+
```

### 2.2. Diagrama de Arquitectura del Sistema (C4 Container View)

> **[AS-IS] en negrita, [TO-BE] en cursiva.** SA1-SA6, pysteps, LightGBM, GOES/CAMS/ERA5 ingest, Redis pub/sub y TimescaleDB continuo son TO-BE (no cableados hoy).

```mermaid
flowchart TD
    subgraph HARDWARE["1. Capa de Hardware IoT"]
        ESP["Nodo IoT ESP32 (BME280 + Pluviómetro + Anemómetro)"]
    end

    subgraph INGESTA["2. Ingesta & Protocolos de Comunicación"]
        MQTT_BROKER["Mosquitto MQTT Broker (Puerto 1883)"]
        APIS_EXT["APIs Externas (Open-Meteo, NOAA GOES-16 S3, CAMS AOD)"]
    end

    subgraph PROCESAMIENTO["3. Núcleo Físico & ML (Coste $0 Tokens)"]
        SA1["SA1: Ingesta, QC & Filtro Kalman Adaptativo"]
        SA2["SA2: Motor Termodinámico (MetPy)"]
        SA3["SA3: Nowcasting Radar & Flujo Óptico (pysteps)"]
        SA4["SA4: Super-Ensemble & Downscaling (LightGBM)"]
    end

    subgraph COGNITIVO["4. Capa Cognitiva, FastMCP & LLM Gateway"]
        ORQ["Orquestador Master / Router (Plan-and-Execute)"]
        LLM_GW["LLM Gateway (OpenAI / OpenRouter / DeepSeek / Ollama / vLLM)"]
        SA5["SA5: Verificación, CRPS & Calibración Closed-Loop"]
        SA6["SA6: Análisis de Riesgo Hidrológico & Difusión"]
        KG[("Graphify GraphRAG (graph.json / Comunidades Louvain)")]
    end

    subgraph PERSISTENCIA["5. Almacenamiento & Caché"]
        TSDB[("TimescaleDB (Hypertables & Vistas Continuas 5m)")]
        REDIS[("Redis (Pub/Sub & State Cache)")]
    end

    subgraph PRESENTACION["6. Presentación & Consumidores"]
        DASH["Dashboard Web Reactivo (HTML5 + WebSockets + ECharts)"]
        ALERT_CHANNELS["Difusión Ciudadana (WhatsApp, Telegram, X)"]
    end

    ESP -->|MQTT QoS 1| MQTT_BROKER
    MQTT_BROKER --> SA1
    APIS_EXT --> SA1
    APIS_EXT --> SA3
    APIS_EXT --> SA4

    SA1 --> SA2
    SA1 --> SA4
    SA2 --> ORQ
    SA3 --> ORQ
    SA4 --> ORQ

    ORQ <--> LLM_GW
    ORQ <--> KG
    ORQ <--> SA5
    ORQ --> SA6

    SA1 --> TSDB
    SA5 --> TSDB
    ORQ --> REDIS
    REDIS --> DASH
    SA6 --> ALERT_CHANNELS
    SA6 --> DASH
```

---

## 3. Configuración de Modelos y Pasarela LLM (*Provider-Agnostic Gateway*)

El sistema utiliza un adaptador universal de endpoints compatibles con OpenAI (`/v1/chat/completions`) que permite al usuario configurar cualquier proveedor o plan por tokens:

```
+---------------------------------------------------------------------------------------------------------------+
| PROVEEDOR / SERVICIO        | EJEMPLO BASE URL                                | EJEMPLO MODELO RECOMENDADO    |
+-----------------------------+-------------------------------------------------+-------------------------------+
| OpenAI                      | https://api.openai.com/v1                       | gpt-4o, gpt-4o-mini           |
| OpenRouter (Multi-Provider) | https://openrouter.ai/api/v1                    | deepseek/deepseek-r1, qwen-72b|
| DeepSeek API                | https://api.deepseek.com/v1                     | deepseek-chat, deepseek-reasoner|
| Groq (Ultra-Fast)           | https://api.groq.com/openai/v1                  | llama-3.3-70b-versatile       |
| Inferencia Local (Ollama)   | http://localhost:11434/v1                       | qwen2.5:72b, deepseek-r1:14b  |
| Inferencia Local (vLLM)     | http://localhost:8000/v1                        | custom-finetuned-weather      |
+---------------------------------------------------------------------------------------------------------------+
```

### Variables de Entorno de Configuración (`.env` — requiere `python-dotenv`):

> `LLM_PROVIDER` es etiqueta informativa (no cambia el gateway). `DATABASE_URL/REDIS_URL/MQTT_*` y `ENVIRONMENT/PORT/HOST` son **TO-BE** (no leídos hoy). Efectivos: `LLM_BASE_URL`, `LLM_API_KEY`, `ORCHESTRATOR_*`, `RISK_AGENT_*`.

```bash
# Gateway y Autenticación — requiere load_dotenv() (ver orchestrator.py)
LLM_PROVIDER=openai                       # etiqueta, no usada por el gateway
LLM_BASE_URL=https://api.openai.com/v1    # endpoint compatible con chat/completions
LLM_API_KEY=tu_api_key_aqui               # vacío o placeholder → fallback determinista

# Modelos y límites — SÍ efectivos (defaults si faltan: 250/300 y 0.3)
ORCHESTRATOR_MODEL=gpt-4o-mini            # modelo para resumen ejecutivo
ORCHESTRATOR_MAX_TOKENS=250              # límite resumen (antes hardcodeado 2000)
ORCHESTRATOR_TEMPERATURE=0.3

RISK_AGENT_MODEL=gpt-4o-mini              # modelo para boletín ciudadano
RISK_AGENT_MAX_TOKENS=300
RISK_AGENT_TEMPERATURE=0.3
```

---

## 4. Especificación de los Subagentes del Sistema

> **[AS-IS] implementado:** `WeatherOrchestrator` + 4 tools FastMCP. **[TO-BE]** SA1-SA6 como módulos independientes, AKF, Z-Score, pysteps, LightGBM, CRPS/EMA.

```
+-------------------------------------------------------------------------------------------------------------------+
| ID  | SUBAGENTE                     | TIPO DE PROCESO      | MOTOR / HERRAMIENTAS  | CONSUMO TOKENS               | ESTADO |
+-----+-------------------------------+----------------------+-----------------------+------------------------------+--------+
| ORQ | Orquestador Master / Router   | Cognitivo (CoT)      | LLM Gateway (Usuario) | Variable (Solo bajo demanda) | AS-IS  |
| SA1 | Ingesta, QC & Asimilación     | Determinista Puro    | Python / Kalman AKF   | 0 Tokens (100% Determinista) | TO-BE  |
| SA2 | Motor Termodinámico           | Físico Determinista  | MetPy / SciPy         | 0 Tokens (100% Determinista) | AS-IS* |
| SA3 | Nowcasting Radar & Satélite   | Visión / Flujo Óptico| pysteps / Lucas-Kanade| 0 Tokens (100% Determinista) | TO-BE  |
| SA4 | Super-Ensemble & Downscaling  | Machine Learning     | LightGBM / Cuantiles  | 0 Tokens (100% Determinista) | TO-BE  |
| SA5 | Verificación & Closed-Loop    | Estadístico          | SQL / TimescaleDB     | 0 Tokens (100% Determinista) | TO-BE  |
| SA6 | Riesgo por Cuenca & Difusión  | Cognitivo / Síntesis | LLM Gateway (Usuario) | Bajo (< 500 tokens por aviso)| AS-IS* |
| KG  | Grafo de Conocimiento         | GraphRAG Estructurado| Graphify CLI          | Fijo (--budget 1500)         | AS-IS* |
+-------------------------------------------------------------------------------------------------------------------+
* SA2/KG/SA6 parciales: SA2 usa umbrales absolutos (no deltas 3h); KG solo query; SA6 semáforo sí pero sin modelo de cuenca.
```

---

### 4.1. Orquestador Master (`MasterOrchestrator`)
- **Responsabilidad:** Centro neurálgico del sistema. Coordina la ejecución de herramientas FastMCP, evalúa la intención del usuario y gestiona contingencias si una API externa degrada.

### 4.2. Subagente 1: Ingesta, QC & Asimilación (`DataIngestionAgent`) — **[TO-BE]**
- **Filtro Modified Z-Score:** Rechazo de anomalías y ruido de sensores físicos ($|M_i| > 3.5$).
- **Filtro de Kalman Adaptativo (AKF):**
  $$\\hat{x}_{k|k} = \\hat{x}_{k|k-1} + K_k (z_k - H \\hat{x}_{k|k-1})$$
- **AS-IS real:** validación simple en `mcp_server.py:16-19` (`temp>45` o `hum>100` → `qc.is_valid=false`); `SensorQualityControl` expone campos sin cálculo.

### 4.3. Subagente 2: Motor Termodinámico (`ThermoPhysicsAgent`) — **[AS-IS parcial]**
- **Cálculo Determinista con `MetPy`:** Punto de rocío ($T_d$), Nivel $LCL$, $CAPE$ (J/kg), $CIN$ (J/kg) y Agua Precipitable $PWAT$ (mm). Con fallback heurístico si MetPy no está.
- **Detección de "Norte" [AS-IS]:** umbrales absolutos `P>864 hPa ∧ T<18°C ∧ Dir∈[300,360]∪[0,30]` (`physics_engine.py:85`). **[TO-BE] spec regional por deltas:** $\\Delta P_{3\\text{h}} \\ge +2.5\\,\\text{hPa} \\land \\text{Dir}_{\\text{viento}} \\in [300^\\circ, 360^\\circ] \\land \\text{Racha} \\ge 50\\,\\text{km/h} \\land \\Delta T_{3\\text{h}} \\le -4.0\\,^\\circ\\text{C}$ (ver memoria §2.1, no implementado).

### 4.4. Subagente 3: Nowcasting Radar & Satélite (`NowcastAgent`) — **[TO-BE]**
- **Flujo Óptico semilagrangiano de Lucas-Kanade (`pysteps`):** Proyección de reflectividad radar a 0-120 minutos e ingesta GOES-16 Banda 13 IR + GLM. *Sin evidencia en código (no en requirements ni app/).*

### 4.5. Subagente 4: Super-Ensemble & Downscaling ML (`MLEnsembleAgent`) — **[TO-BE]**
- **Ensamble Multi-Modelo:** Fusión de `ECMWF`, `GFS`, `ICON`, `HRRR`.
- **Regresión por Cuantiles con LightGBM:** Estimación de probabilidad orográfica ($p_{10}, p_{50}, p_{90}$) para la cuenca de Xalapa. *AS-IS: ensamble sintético pseudoaleatorio en `orchestrator.py:163-189`; no LightGBM.*

### 4.6. Subagente 5: Verificación & Closed-Loop (`FeedbackCalibrationAgent`) — **[TO-BE]**
- **Métricas:** $MAE$, $RMSE$, $CRPS$, $CSI$ (Threat Score).
- **Autocalibración:** Actualización de pesos del ensamble en base de datos mediante Exponential Moving Average (EMA). *Tabla `forecast_verification_log` existe en SQL pero nadie la escribe.*

### 4.7. Subagente 6: Riesgo Hidrológico & Difusión (`RiskSocialAgent`) — **[AS-IS parcial]**
- **Monitoreo de Cuencas:** Río Actopan, Río La Antigua, Río Sordo. *Nombres solo en docstring/acciones de texto.*
- **Semáforo de 4 Niveles:** 🟢 Verde, 🟡 Amarillo, 🟠 Naranja, 🔴 Rojo. **[AS-IS]** umbrales en `mcp_server.py:46-96`.
- **Formateador Multicanal:** Generación de boletines con emojis para WhatsApp, Telegram y X vía el LLM configurado. **[AS-IS]** con fallback determinista.

---

## 5. Capa Transversal: Grafo de Conocimiento Graphify (GraphRAG)

- **Indexación [AS-IS]:** Grafo en `graphify-out/graph.json` con comunidades Louvain (`build_graph.py`).
- **Herramientas FastMCP:**
  ```python
  graphify_query(question: str, budget_tokens: int = 1500) -> str  # AS-IS
  graphify_find_path(concept_a: str, concept_b: str) -> str        # TO-BE (no existe)
  graphify_explain_node(node_id: str) -> str                        # TO-BE (no existe)
  ```
  Solo `query_graphify_knowledge` está cableado (`mcp_server.py:100-111`); `find_path`/`explain` son TO-BE.

---

## 6. Diseño de Interfaz y Dashboard en Tiempo Real

- **Streaming WebSockets [AS-IS]:** `/ws/telemetry/live` cada **2 s (0.5 Hz)** (`main.py:107` `asyncio.sleep(2)`). Docs previos decían 1 Hz — corregido.
- **Componentes [AS-IS]:**
  - 5 Tarjetas métricas en vivo.
  - Gráfica de series de tiempo 24h interactiva con Apache ECharts.
  - Gauge de convección $CAPE$ ($0 - 3,500\\,\\text{J/kg}$).
  - Abanico de cuantiles probabilísticos a 14 días ($p_{10}, p_{50}, p_{90}$) **sintético** (pseudoaleatorio, no multi-modelo; frontend grafica `p50/p90`).
  - Visor de alertas de Protección Civil y caja de consulta Graphify GraphRAG.

---

## 7. Diseño de Hardware IoT y Firmware ESP32

- **Microcontrolador:** ESP32-WROOM-32 (Dual Core 240MHz).
- **Sensores:** BME280 (I2C), Pluviómetro de balancín (GPIO 4), Anemómetro (GPIO 5), Divisor de voltaje batería (GPIO 34).
- **Protocolo:** MQTT con calidad de servicio **QoS 1** y reconexión automática.

---

## 8. Esquema de Persistencia TimescaleDB (DDL)

> **[AS-IS]** `sensor_telemetry` como hypertable sí existe en `database/init.sql`. **[TO-BE]** la vista continua `telemetry_5min` solo vive en este doc (no en SQL). El SQL real además crea `forecast_verification_log` y `weather_alerts` (no documentadas aquí antes) — añadidas abajo.

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS sensor_telemetry (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    station_id VARCHAR(32) NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    humidity_pct DOUBLE PRECISION NOT NULL,
    pressure_hpa DOUBLE PRECISION NOT NULL,
    rain_rate_mmh DOUBLE PRECISION DEFAULT 0.0,
    rain_accum_24h_mm DOUBLE PRECISION DEFAULT 0.0,
    wind_speed_kmh DOUBLE PRECISION DEFAULT 0.0,
    wind_gust_kmh DOUBLE PRECISION DEFAULT 0.0,
    wind_direction_deg DOUBLE PRECISION DEFAULT 0.0,
    battery_v DOUBLE PRECISION DEFAULT 4.2,
    qc_valid BOOLEAN DEFAULT TRUE
);

SELECT create_hypertable('sensor_telemetry', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);

-- [TO-BE] Vista continua 5 min — NO está en database/init.sql actual (solo en este doc)
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_5min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    station_id,
    AVG(temperature_c) AS avg_temp,
    MAX(temperature_c) AS max_temp,
    MIN(temperature_c) AS min_temp,
    AVG(humidity_pct) AS avg_humidity,
    AVG(pressure_hpa) AS avg_pressure,
    SUM(rain_rate_mmh * (5.0 / 60.0)) AS accum_rain_mm,
    MAX(wind_speed_kmh) AS max_wind_gust
FROM sensor_telemetry
WHERE qc_valid = TRUE
GROUP BY bucket, station_id;

-- [AS-IS en SQL, no documentadas antes] Verificación y alertas (existen en database/init.sql)
-- forecast_verification_log y weather_alerts — ver database/init.sql
```

---

## 9. Despliegue con Docker Compose

> **Corregido post-auditoría:** el compose real antes no inyectaba `LLM_*` y montaba `.:/app` genérico. Ahora usa `env_file: .env` + volúmenes acotados + healthcheck del app. Ver `docker-compose.yml`.

```yaml
version: "3.8"

services:
  orchestrator:
    build: .
    container_name: ivekbot_orchestrator
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://ivek_user:***@timescaledb:5432/weather_db
      - REDIS_URL=redis://redis:6379/0
      - OPEN_METEO_API=https://api.open-meteo.com/v1
      # LLM_* vía env_file; sin .env caen a defaults del orquestador
    volumes:
      - ./app:/app/app:ro
      - ./static:/app/static:ro
    depends_on:
      timescaledb:
        condition: service_healthy
      mqtt_broker:
        condition: service_started
      redis:
        condition: service_healthy

  mqtt_broker:
    image: eclipse-mosquitto:latest
    container_name: ivekbot_mqtt
    restart: unless-stopped
    ports:
      - "1883:1883"
    volumes:
      - mosquitto_data:/mosquitto/data
      - mosquitto_log:/mosquitto/log

  timescaledb:
    image: timescale/timescaledb:latest-pg15
    container_name: ivekbot_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ivek_user
      POSTGRES_PASSWORD: ivek_pass
      POSTGRES_DB: weather_db
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ivek_user -d weather_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: ivekbot_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  db_data:
  mosquitto_data:
  mosquitto_log:
```
