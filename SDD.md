# Software Design Document (SDD)
## Documento de Diseño de Software: Estación Meteorológica Digital Multi-Agente (*IvekBot Weather Station*)

- **Document ID:** SDD-IVEKBOT-WX-2026-V1
- **Versión:** 1.0.0 (Release Productivo)
- **Fecha:** 2026-08-14
- **Estándar:** IEEE 1016-2009 (Software Design Descriptions), FastMCP, Pydantic v2, TimescaleDB, Docker
- **Ubicación Geográfica de Referencia:** Xalapa, Veracruz, México ($19.54^\circ\text{N},\, 96.92^\circ\text{W}$, Altitud: $1,420\,\text{msnm}$)

---

## 1. Introducción y Filosofía del Sistema

### 1.1. Objetivo General
Diseñar y construir un ecosistema meteorológico digital autónomo, de alta disponibilidad, modular y con capacidad de razonamiento cognitivo. El sistema supera a las estaciones tradicionales combinando **telemetría física de superficie**, **motores deterministas de física atmosférica**, **modelos numéricos y neuronales globales (NWP / AI-NWP)**, **orquestación multi-agente vía FastMCP**, **GraphRAG con Graphify** y un **Dashboard reactivo en tiempo real**.

### 1.2. Principios Rectores de Diseño
1. **Separación Estricta entre Lógica Determinista y Razonamiento Cognitivo:**
   - Todo cálculo matemático, termodinámico y de extrapolación de sensores se ejecuta en Python puro / C++ sin intervención de LLMs, garantizando **cero alucinaciones** y **coste $0$ de tokens** en la operación continua baseline.
   - Los Modelos de Lenguaje (LLMs) se activan de forma quirúrgica únicamente para interpretar escenarios complejos, evaluar riesgos por cuenca, consultar el grafo de conocimiento y redactar boletines de Protección Civil.
2. **Eficiencia Extrema de Tokens (GraphRAG con Graphify):**
   - La base de conocimiento sobre el código, reglas sinópticas y manuales de Protección Civil se indexa en un grafo con comunidades de Louvain, permitiendo consultas contextuales con un presupuesto estricto (`--budget 1500`).
3. **Resiliencia Operativa y Degradación Elegante (*Graceful Degradation*):**
   - Si la conexión a internet cae, el nodo IoT almacena lecturas en flash y el servidor continúa computando tendencias locales sin detenerse.

---

## 2. Arquitectura General y Separación de Fases

### 2.1. Desacoplamiento: Desarrollo vs. Operación (Runtime 24/7)

```
+---------------------------------------------------------------------------------------------------------------+
| FASE              | ACTORES / HERRAMIENTAS              | RESPONSABILIDAD TÉCNICA                             |
+-------------------+-------------------------------------+-----------------------------------------------------+
| DESARROLLO        | Desarrollador + DeepSeek-V3 /       | Construcción de código, definición de esquemas,     |
| (Build-Time)      | Qwen-2.5-Coder-32B                  | entrenamiento de modelos ML y compilación Graphify. |
+-------------------+-------------------------------------+-----------------------------------------------------+
| OPERACIÓN         | Orquestador Master + 6 Subagentes   | Ingesta 1 Hz por MQTT, física MetPy, pysteps radar, |
| (Runtime 24/7)    | + FastAPI + TimescaleDB + WebSockets| difusión WebSocket y emisión de alertas ciudadanas. |
+---------------------------------------------------------------------------------------------------------------+
```

### 2.2. Diagrama de Arquitectura del Sistema (C4 Container View)

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

    subgraph COGNITIVO["4. Capa Cognitiva & FastMCP (LLMs Quirúrgicos)"]
        ORQ["Orquestador Master / Router (DeepSeek-R1 / Gemini 1.5 Pro)"]
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

## 3. Especificación de los Subagentes del Sistema

```
+-------------------------------------------------------------------------------------------------------------------+
| ID  | SUBAGENTE                     | TIPO DE PROCESO      | MODELO / MOTOR        | CONSUMO TOKENS               |
+-----+-------------------------------+----------------------+-----------------------+------------------------------+
| ORQ | Orquestador Master / Router   | Cognitivo (CoT)      | DeepSeek-R1 / Gemini  | Variable (Solo bajo demanda) |
| SA1 | Ingesta, QC & Asimilación     | Determinista Puro    | Python / Kalman AKF   | 0 Tokens (100% Determinista) |
| SA2 | Motor Termodinámico           | Físico Determinista  | MetPy / SciPy         | 0 Tokens (100% Determinista) |
| SA3 | Nowcasting Radar & Satélite   | Visión / Flujo Óptico| pysteps / Lucas-Kanade| 0 Tokens (100% Determinista) |
| SA4 | Super-Ensemble & Downscaling  | Machine Learning     | LightGBM / Cuantiles  | 0 Tokens (100% Determinista) |
| SA5 | Verificación & Closed-Loop    | Estadístico          | SQL / TimescaleDB     | 0 Tokens (100% Determinista) |
| SA6 | Riesgo por Cuenca & Difusión  | Cognitivo / Síntesis | Qwen-2.5-72B / DSeek  | Bajo (< 800 tokens por aviso)|
| KG  | Grafo de Conocimiento         | GraphRAG Estructurado| Graphify CLI          | Fijo (--budget 1500)         |
+-------------------------------------------------------------------------------------------------------------------+
```

---

### 3.1. Orquestador Master (`MasterOrchestrator`)
- **Responsabilidad:** Centro neurálgico del sistema. Recibe triggers (cron cada 5 min, WebSockets o eventos de sensor) y orquesta el flujo de llamadas a herramientas FastMCP.
- **Patrón:** *Plan-and-Execute* con validación de esquemas Pydantic v2.
- **Manejo de Fallbacks:** Si un sensor físico pierde conexión, conmuta a estimación por satélite/ERA5 con bandera de advertencia.

---

### 3.2. Subagente 1: Ingesta, QC & Asimilación (`DataIngestionAgent`)
- **Control de Calidad (QC):** Filtro *Modified Z-Score* sobre ventana de 15 minutos:
  $$M_i = \frac{0.6745 \cdot (x_i - \tilde{x})}{\text{MAD}}$$
  Rechaza lecturas si $|M_i| > 3.5$ (eliminación de falsos picos térmicos o eléctricos).
- **Filtro de Kalman Adaptativo (AKF):**
  Corrige la deriva de la estación física $z_k$ en función de la covarianza del error de medición $R_k$ y de proceso $Q_k$:
  $$\hat{x}_{k|k} = \hat{x}_{k|k-1} + K_k (z_k - H \hat{x}_{k|k-1})$$
  $$K_k = P_{k|k-1} H^T (H P_{k|k-1} H^T + R_k)^{-1}$$

---

### 3.3. Subagente 2: Motor Termodinámico (`ThermoPhysicsAgent`)
- **Librería Central:** `MetPy` con manejo de unidades dimensionales estrictas.
- **Fórmulas Principales:**
  - **Punto de Rocío ($T_d$):**
    $$T_d = \frac{237.7 \cdot \alpha}{17.27 - \alpha}, \quad \text{donde } \alpha = \frac{17.27 \cdot T}{237.7 + T} + \ln\left(\frac{RH}{100}\right)$$
  - **Nivel de Condensación por Elevación ($LCL$):**
    Presión barométrica donde una parcela se satura adiabáticamente.
  - **Energía Convectiva ($CAPE$) e Inhibición ($CIN$):**
    $$CAPE = \int_{z_{LFC}}^{z_{EL}} g \left( \frac{T_{v,\text{parcela}} - T_{v,\text{entorno}}}{T_{v,\text{entorno}}} \right) dz$$
    $$CIN = \int_{z_{\text{superficie}}}^{z_{LFC}} g \left( \frac{T_{v,\text{parcela}} - T_{v,\text{entorno}}}{T_{v,\text{entorno}}} \right) dz$$
  - **Detección de "Norte" (Frente Frío Polar):**
    Disparo de bandera activa si:
    $$\Delta P_{3\text{h}} \ge +2.5\,\text{hPa} \quad \land \quad 300^\circ \le \text{Dir}_{\text{viento}} \le 360^\circ \quad \land \quad \text{Racha} \ge 50\,\text{km/h} \quad \land \quad \Delta T_{3\text{h}} \le -4.0\,^\circ\text{C}$$

---

### 3.4. Subagente 3: Nowcasting Radar & Satélite (`NowcastAgent`)
- **Algoritmo:** Flujo óptico semilagrangiano de *Lucas-Kanade* implementado en `pysteps`.
- **Rango Operativo:** Proyección de reflectividad radar ($dBZ$) de 0 a 120 minutos en intervalos de 5 min.
- **Entrada Satelital:** GOES-16 Banda 13 ($10.3\,\mu\text{m}$) para seguimiento de cimas de nubes convectivas frías ($<-50\,^\circ\text{C}$) y pulsos de rayos GLM.

---

### 3.5. Subagente 4: Super-Ensemble & Downscaling ML (`MLEnsembleAgent`)
- **Modelos Integrados:** `ECMWF IFS/AIFS`, `NOAA GFS`, `DWD ICON`, `NCEP HRRR`.
- **Downscaling Estadístico con LightGBM:**
  - Modelo de regresión por cuantiles para lluvia a 14 días ($p_{10}, p_{50}, p_{90}$) entrenado con reanálisis ERA5 de 30 años ajustado a la altitud real de Xalapa ($1,420\,\text{msnm}$).

---

### 3.6. Subagente 5: Verificación & Closed-Loop (`FeedbackCalibrationAgent`)
- **Frecuencia:** Ejecución cada 24 horas para comparar pronósticos emitidos vs. observaciones reales de la estación física.
- **Métricas de Rendimiento:**
  - $MAE = \frac{1}{n} \sum |Y_t - \hat{Y}_t|$
  - $RMSE = \sqrt{\frac{1}{n} \sum (Y_t - \hat{Y}_t)^2}$
  - $CRPS(F, y) = \int_{-\infty}^\infty \left[ F(x) - \mathbf{1}(x \ge y) \right]^2 dx$
  - $CSI = \frac{\text{Aciertos}}{\text{Aciertos} + \text{Fallos} + \text{Falsas Alarmas}}$
- **Autocalibración:** Actualización de pesos del ensamble mediante Media Móvil Exponencial (EMA) del inverso del CRPS.

---

### 3.7. Subagente 6: Análisis de Riesgo Hidrológico & Difusión (`RiskSocialAgent`)
- **Monitoreo de Cuencas:**
  - Cuenca Río Actopan, Cuenca Río La Antigua, Cuenca Río Sordo.
- **Matriz de Alerta:**
  - 🟢 **VERDE:** Precipitación acumulada $<10\,\text{mm}$, viento normal.
  - 🟡 **AMARILLO:** Lluvia $10-30\,\text{mm}$, niebla densa ($LCL < 1,450\,\text{msnm}$).
  - 🟠 **NARANJA:** Lluvia $>45\,\text{mm}/3\text{h}$, rachas $>55\,\text{km/h}$ o Frente Frío severo.
  - 🔴 **ROJO:** Lluvia acumulada $>100\,\text{mm}/24\text{h}$ o riesgo de desbordamiento/deslave.
- **Formateador Multicanal:** Generación de avisos estructurados con emojis para WhatsApp, Telegram y X.

---

## 4. Capa Transversal: Grafo de Conocimiento Graphify (GraphRAG)

### 4.1. Estructura y Detección de Comunidades
Graphify indexa el repositorio en `graphify-out/graph.json` particionando el conocimiento mediante el algoritmo **Louvain/Leiden**:
- **Comunidad 0 (Física & Modelado):** `physics_engine.py`, fórmulas de MetPy, índices $CAPE/CIN$, umbrales de Frente Frío.
- **Comunidad 1 (Ingesta & Protocolos IoT):** `esp32_sensor_node.py`, MQTT, filtros de ruido, esquemas Pydantic.
- **Comunidad 2 (Orquestación & FastMCP):** `orchestrator.py`, `mcp_server.py`, endpoints FastAPI, WebSockets.
- **Comunidad 3 (Protección Civil & Cuencas):** Reglas operativas de ríos Actopan/La Antigua, protocolos de evacuación.

### 4.2. Herramientas MCP Expuestas
```python
graphify_query(question: str, budget_tokens: int = 1500) -> str
graphify_find_path(concept_a: str, concept_b: str) -> str
graphify_explain_node(node_id: str) -> str
```

---

## 5. Diseño de Interfaz y Dashboard en Tiempo Real

### 5.1. Protocolo WebSockets (`/ws/telemetry/live`)
- **Latencia:** Sub-segundo ($1\,\text{Hz}$).
- **Estructura del Paquete JSON:**
```json
{
  "type": "telemetry_pulse",
  "telemetry": {
    "temperature_c": 24.5,
    "humidity_pct": 84.0,
    "pressure_hpa": 861.2,
    "rain_rate_mmh": 1.2,
    "rain_accum_24h_mm": 14.5,
    "wind_speed_kmh": 15.0,
    "wind_gust_kmh": 26.0
  },
  "thermodynamics": {
    "dewpoint_c": 21.6,
    "cape_jkg": 1720.0,
    "cin_jkg": -28.0,
    "pwat_mm": 42.1,
    "norte_surge_detected": false
  }
}
```

### 5.2. Componentes de UI (HTML5 + Vanilla CSS + Apache ECharts)
1. **Header Reactivo:** Estado de conexión WebSocket en vivo y badge de nivel de alerta.
2. **5 Tarjetas de Métricas:** Temperatura, Humedad, Presión, Viento/Racha, Lluvia 24h.
3. **Gráfica de Series de Tiempo 24h:** Curvas de temperatura, humedad y presión con zoom dinámico.
4. **Gauge de Convección (CAPE):** Aguja de 0 a 3,500 J/kg con zonas Verde, Ámbar y Roja.
5. **Abanico Probabilístico 14 Días:** Barras para $p_{50}$ y líneas para $p_{90}$.
6. **Buscador Graphify:** Caja de texto para consultas semánticas al grafo de conocimiento.

---

## 6. Diseño de Hardware IoT y Firmware ESP32

```
+---------------------------------------------------------------------------------------------------+
| COMPONENTE               | MODELO / ESPECIFICACIÓN              | INTERFAZ / PROTOCOLO            |
+--------------------------+--------------------------------------+---------------------------------+
| Microcontrolador Central | ESP32-WROOM-32 (Dual Core 240MHz)    | Wi-Fi 802.11 b/g/n / MicroPython|
| Sensor Termohigrométrico | Bosch BME280                         | I2C (Dirección 0x76 / 0x77)     |
| Pluviómetro              | Pluviómetro de balancín (0.2794 mm)  | GPIO 4 (Interrupción por pulso) |
| Anemómetro               | Sensor de efecto Hall / Cazoletas    | GPIO 5 (Conteo de frecuencia)   |
| Alimentación & Batería   | Batería LiPo 3.7V + Panel Solar 6V   | ADC GPIO 34 (Divisor resistivo) |
+---------------------------------------------------------------------------------------------------+
```

- **Protocolo de Red:** MQTT con calidad de servicio **QoS 1** (garantía de entrega) y reconexión automática en caso de caída de WiFi.

---

## 7. Esquema de Persistencia TimescaleDB (DDL)

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. Hypertable de telemetría física (partición de 7 días)
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

-- 2. Vista agregada continua de 5 minutos
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

-- 3. Tabla de auditoría y verificación continua
CREATE TABLE IF NOT EXISTS forecast_verification_log (
    id BIGSERIAL PRIMARY KEY,
    forecast_id VARCHAR(64) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    valid_for TIMESTAMPTZ NOT NULL,
    predicted_temp DOUBLE PRECISION,
    observed_temp DOUBLE PRECISION,
    predicted_rain_mm DOUBLE PRECISION,
    observed_rain_mm DOUBLE PRECISION,
    error_mae DOUBLE PRECISION,
    crps_score DOUBLE PRECISION,
    model_weights_json JSONB
);
```

---

## 8. Despliegue con Docker Compose

```yaml
version: "3.8"

services:
  orchestrator:
    build: .
    container_name: ivekbot_orchestrator
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://ivek_user:ivek_pass@timescaledb:5432/weather_db
      - REDIS_URL=redis://redis:6379/0
      - OPEN_METEO_API=https://api.open-meteo.com/v1
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

---

## 9. Trazabilidad de Requerimientos y Validación

```
+------------------------------------+-----------------------------------+-----------------------------------+
| REQUERIMIENTO                      | COMPONENTE RESPONSABLE            | CRITERIO DE ACEPTACIÓN            |
+------------------------------------+-----------------------------------+-----------------------------------+
| Telemetría en tiempo real          | ESP32 + MQTT + WebSockets         | Latencia < 1000 ms en dashboard   |
| Cero alucinaciones físicas         | Subagente 2 (MetPy)               | 100% de índices vía fórmulas exactas|
| Predicción de tormentas severas    | Subagente 3 (pysteps)             | Nowcasting radar a 0-120 min      |
| Pronóstico probabilístico orográfico| Subagente 4 (LightGBM)           | Cuantiles p10, p50, p90 a 14 días |
| Ahorro de tokens en LLMs           | Graphify GraphRAG                 | Consultas acotadas a budget <1500t|
| Calibración continua               | Subagente 5 (Feedback Loop)       | Actualización de pesos CRPS/MAE   |
| Alertas públicas multicanal        | Subagente 6 (Risk & Social)       | Clasificación en 4 niveles semáforo|
+------------------------------------+-----------------------------------+-----------------------------------+
```
