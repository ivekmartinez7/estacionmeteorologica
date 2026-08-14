# Arquitectura y Metodología Integral: Estación Meteorológica Digital Multi-Agente, Graphify (GraphRAG) & Dashboard en Tiempo Real

- **Proyecto:** Estación Meteorológica Digital con Agentes e Inteligencia Artificial (*IvekBot Weather Station*)
- **Estándar:** Model Context Protocol (MCP), FastMCP, Graphify (GraphRAG), FastAPI, WebSockets, TimescaleDB, Docker, Apache ECharts / Leaflet
- **Ubicación de Referencia:** Xalapa, Veracruz, México ($19.54^\circ\text{N},\, 96.92^\circ\text{W}$, Altitud: $1,420\,\text{msnm}$) — Microclima de Bosque de Niebla y Alta Orografía

---

## 1. Resumen Ejecutivo y Filosofía del Sistema

El ecosistema meteorológico integra **física determinista**, **modelos numéricos / neuronales (AI-NWP)**, **orquestación multi-agente vía MCP**, **GraphRAG con Graphify para contexto semántico de bajo costo en tokens**, y un **Dashboard de visualización reactiva en tiempo real**.

```
+---------------------------------------------------------------------------------------------------+
| 1. CAPA DETERMINISTA & FÍSICA     | Ecuaciones de termodinámica atmosférica (MetPy), asimilación  |
|    (Cero Alucinaciones)           | local (Filtro de Kalman Adaptativo) y nowcasting (pysteps).   |
+-----------------------------------+---------------------------------------------------------------+
| 2. CAPA NUMÉRICA & ML (AI-NWP)    | Ensamble multi-modelo (ECMWF, GFS, ICON, HRRR, GraphCast) con |
|    (Predicción y Downscaling)     | corrección estadística de sesgo orográfico vía LightGBM.      |
+-----------------------------------+---------------------------------------------------------------+
| 3. GRAPHRAG CON GRAPHIFY          | Grafo de conocimiento navegable para LLMs: indexación de      |
|    (Memoria y Contexto Eficiente) | código, reglas sinópticas y cuencas con detección comunidades.|
+-----------------------------------+---------------------------------------------------------------+
| 4. CAPA COGNITIVA MULTI-AGENTE    | Orquestación con FastMCP, síntesis de riesgo hidrometeorológico|
|    (Razonamiento y Difusión)      | y generación automatizada de alertas públicas.                |
+-----------------------------------+---------------------------------------------------------------+
| 5. CAPA DE INTERFAZ & DASHBOARD   | WebSockets para telemetría sub-segundo, gráficas interactivas |
|    (Visualización en Tiempo Real) | (ECharts), mapas radar (Leaflet) y control de alertas.        |
+-----------------------------------+---------------------------------------------------------------+
```

---

## 2. Métodos del Estado del Arte en Pronóstico Meteorológico

```
+-------------------------------------------------------------------------------------------------------------+
| HORIZONTE             | FENÓMENO OBJETIVO                 | METODOLOGÍA Y MODELOS UTILIZADOS                |
+-----------------------+-----------------------------------+-------------------------------------------------+
| Nowcasting (0 - 6 h)  | Tormentas convectivas, granizo,   | Flujo Óptico (Lucas-Kanade) con pysteps,        |
|                       | ráfagas de viento y niebla local  | GOES-16 Banda 13 IR (10.3um) + GLM, MetPy       |
+-----------------------+-----------------------------------+-------------------------------------------------+
| Corto / Medio Plazo   | Frentes Fríos ("Nortes"), Ondas   | Super-Ensemble NWE (ECMWF IFS/AIFS, GFS, ICON,  |
| (6 h - 14 días)       | Tropicales, Lluvias Acumuladas    | HRRR) + Downscaling Estadístico con LightGBM    |
+-----------------------+-----------------------------------+-------------------------------------------------+
| Sub-estacional / S2S  | Anomalías de precipitación,       | MJO (Fases RMM1/RMM2), CAMS AOD (Polvo Sahara), |
| (14 días - 3 meses)   | canícula, frentes tardíos         | Climatología ERA5 de 30 años (1991-2020)        |
+-------------------------------------------------------------------------------------------------------------+
```

### 2.1. Dinámica Meteorológica Regional (Caso Xalapa / Barlovento Veracruzano)
1. **Fenómeno del "Norte" (Surge Polar / Advección Baroclínica):**
   - Disparo: Salto barométrico ($\Delta P_{3\text{h}} \ge +2.5\,\text{hPa}$), giro del viento a $330^\circ - 360^\circ$, ráfagas $\ge 50\,\text{km/h}$ y descenso térmico ($\Delta T_{3\text{h}} \le -4.0\,^\circ\text{C}$).
2. **Convección Severa de Verano (Forzamiento Orográfico + Brisa Marina):**
   - Disparo: $\text{CAPE} \ge 1,800\,\text{J/kg}$, $\text{CIN} \ge -40\,\text{J/kg}$, Agua Precipitable $\text{PWAT} \ge 40\,\text{mm}$, Índice de Levantamiento $\text{LI} \le -3.0$.
3. **Niebla Orográfica (*Bosque de Niebla*):**
   - Disparo: Depresión del punto de rocío $(T - T_d \le 0.8\,^\circ\text{C})$ y Nivel de Condensación por Elevación ($\text{LCL} \le 1,450\,\text{msnm}$).

---

## 3. Integración de Graphify (GraphRAG) para Agentes LLM

**Graphify** transforma todo el repositorio (código fuente Python, contratos Pydantic, manuales sinópticos, protocolos de Protección Civil y registros históricos de eventos) en un **Grafo de Conocimiento Estructurado y Persistente** (`graphify-out/graph.json`).

### 3.1. ¿Por qué Graphify para los LLMs en este proyecto?
1. **Reducción de Costo en Tokens (Eficiencia Extrema):** En lugar de inyectar archivos de código completos o documentos extensos en el contexto del LLM, el agente realiza consultas dirigidas sobre el grafo con un presupuesto fijo de tokens (`--budget 1500`).
2. **Detección de Comunidades (Algoritmo Louvain / Leiden):** Agrupa automáticamente conceptos fuertemente vinculados (ej. *Comunidad 1: Protocolos de Inundación de la Cuenca Actopan-La Antigua*, *Comunidad 2: Módulos de Física MetPy*, *Comunidad 3: Pipeline de Telemetría MQTT*).
3. **Navegación de Relaciones Causa-Efecto:** Permite al LLM responder preguntas complejas trazando el camino más corto entre nodos (ej. ¿Cómo se conecta una lectura del sensor barométrico con la activación de la alerta naranja en Protección Civil?).

```
   [Sensor Presión BME280] ──(EMITE_LECTURA)──> [TelemetryData]
                                                        │
                                                (ASIMILADO_POR)
                                                        ▼
   [Alerta Naranja Xalapa] <──(DISPARA_PROTOCOLO)── [Detección Norte] <──(CALCULA_DELTA_P)── [physics_engine.py]
```

### 3.2. Herramientas FastMCP de Graphify para los Agentes

Los subagentes del sistema acceden a Graphify mediante herramientas MCP estándar:

```python
from fastmcp import FastMCP
import subprocess, json

mcp = FastMCP("Graphify-Weather-Knowledge")

@mcp.tool()
def graphify_query(question: str, budget_tokens: int = 1500) -> str:
    """Consulta el grafo de conocimiento del proyecto mediante BFS/DFS sin inflar tokens."""
    cmd = ["graphify", "query", question, "--budget", str(budget_tokens)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else f"Error: {res.stderr}"

@mcp.tool()
def graphify_find_path(concept_a: str, concept_b: str) -> str:
    """Encuentra el camino más corto de dependencias/relaciones entre dos conceptos meteorológicos o módulos."""
    cmd = ["graphify", "path", concept_a, concept_b]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout

@mcp.tool()
def graphify_explain_node(node_id: str) -> str:
    """Genera una explicación contextual concisa de un nodo del sistema (función, sensor, regla climática)."""
    cmd = ["graphify", "explain", node_id]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout
```

---

## 4. Arquitectura General y Flujo de Datos

```mermaid
flowchart TD
    subgraph INGESTA["1. Capa de Ingesta & Hardware IoT"]
        A1["Estación Local Física (ESP32 MQTT QoS 1)"]
        A2["APIs NWP / AI-NWP (ECMWF, GFS, ICON, HRRR)"]
        A3["Satélite GOES-16 (S3 Band 13 IR + GLM)"]
        A4["Radar Doppler Mosaico & ERA5 Climatología"]
    end

    subgraph PROCESAMIENTO["2. Núcleo Físico & Determinista (MetPy & pysteps)"]
        SA1["SA1: Ingesta, QC & Filtro Kalman Adaptativo"]
        SA2["SA2: Motor Termodinámico & Nowcasting"]
        SA3["SA3: Super-Ensemble & Downscaling ML"]
    end

    subgraph CONOCIMIENTO["3. Memoria Estructurada (Graphify GraphRAG)"]
        KG[("graphify-out/graph.json (Knowledge Graph)")]
        COMM["Comunidades Louvain & God Nodes"]
    end

    subgraph COGNITIVO["4. Capa Cognitiva & Orquestación MCP"]
        ORQ["Orquestador Central Master / Router (FastAPI + FastMCP)"]
        SA4["SA4: Verificación, CRPS & Calibración Closed-Loop"]
        SA5["SA5: Análisis de Riesgo Hidrológico & Difusión"]
    end

    subgraph PERSISTENCIA["5. Almacenamiento & Mensajería"]
        DB[("TimescaleDB (Hypertables)")]
        REDIS[("Redis (Pub/Sub & Cache)")]
        AUD["Logs JSON & Calibración"]
    end

    subgraph DASHBOARD["6. Dashboard Reactivo en Tiempo Real"]
        WS["Servidor WebSockets (/ws/telemetry/live)"]
        UI_METRICS["Tarjetas Métricas en Vivo & Gauges"]
        UI_CHARTS["Series de Tiempo & Abanico Cuantiles (ECharts)"]
        UI_SKEWT["Diagrama Skew-T & Índices MetPy"]
        UI_MAP["Mapa Radar / Satélite Interactivo (Leaflet)"]
        UI_ALERTS["Semáforo de Riesgo & Generador Social"]
    end

    A1 --> SA1
    A2 --> SA3
    A3 --> SA2
    A4 --> SA2

    SA1 --> SA2
    SA1 --> SA3
    SA2 --> ORQ
    SA3 --> ORQ

    KG <--> ORQ
    KG <--> SA5

    ORQ <--> SA4
    ORQ --> SA5

    SA1 --> DB
    ORQ --> REDIS
    REDIS --> WS

    WS --> UI_METRICS
    WS --> UI_CHARTS
    WS --> UI_SKEWT
    WS --> UI_MAP
    SA5 --> UI_ALERTS

    SA4 --> AUD
    SA4 -.->|Matriz de Pesos BMA| SA3
```

---

## 5. Jerarquía de Subagentes Especializados

```
+----------------------------------------------------------------------------------------------------+
| AGENTE                     | ENTRADAS                    | SALIDAS TÉCNICAS                        |
+----------------------------+-----------------------------+-----------------------------------------+
| SA1: Ingestion & QC        | Raw MQTT, BME280, Pluviómetro| Telemetría limpia, QC flags, Kalman state|
| SA2: Thermo & Nowcasting   | Sounding data, Radar, GOES  | CAPE, CIN, PWAT, LCL, Vector Flujo Óptico|
| SA3: ML Super-Ensemble     | GFS, ECMWF, HRRR, ERA5, SA1 | $p_{10}, p_{50}, p_{90}$ Lluvia/Temp 14d|
| SA4: Feedback & Audit      | Predicciones vs Realidad 24h| MAE, RMSE, CRPS, Pesos Ensamble (BMA)   |
| SA5: Risk & Social Alert   | Índices SA2, Ensamble, Graph| Semáforo de riesgo y boletín ciudadano  |
+----------------------------------------------------------------------------------------------------+
```

---

## 6. Diseño y Componentes del Dashboard en Tiempo Real

```
+---------------------------------------------------------------------------------------------------+
| HEADER: Estado Conexión [En Vivo] | Estación: Xalapa-01 | Alerta Activa: [AMARILLO - Lluvia]      |
+---------------------------------------------------------------------------------------------------+
| [ PANEL 1: TELEMETRÍA ACTUAL ]  | [ PANEL 2: MAPA RADAR & NOWCASTING ]                            |
| • Temp: 24.5 °C (Sens: 26.1 °C) | • Visor interactivo con capas de reflectividad radar            |
| • Humedad: 86 % | Rocío: 22.0 °C| • Slider temporal (0 a +120 min) generado por pysteps           |
| • Presión: 861.2 hPa (Tend: -1) | • Descargas eléctricas GLM satelitales en tiempo real           |
| • Viento: 16 km/h (Racha: 28) NE|                                                                 |
| • Lluvia: 2.5 mm/h (24h: 18 mm) |                                                                 |
+---------------------------------+-----------------------------------------------------------------+
| [ PANEL 3: SERIES TEMPORALES ]  | [ PANEL 4: TERMODINÁMICA ATMOSFÉRICA (MetPy) ]                  |
| • Gráfica multieje 24h / 7d / 30d| • Diagrama Skew-T log-P interactivo                            |
| • Temperatura, Presión, Lluvia  | • Gauge CAPE (1,850 J/kg) & CIN (-35 J/kg)                      |
| • Zoom y selección de rangos    | • Nivel LCL (890 hPa) y Agua Precipitable (42.5 mm)             |
+---------------------------------+-----------------------------------------------------------------+
| [ PANEL 5: ENSAMBLE 14 DÍAS ]   | [ PANEL 6: ASISTENTE IA, GRAPHRAG & DIFUSIÓN ]                  |
| • Abanico de probabilidad       | • Resumen ejecutivo sintetizado con contexto Graphify           |
|   (Bandas p10 - p50 - p90)      | • Matriz de riesgo por cuenca hidrológica                       |
| • Modelos: ECMWF, GFS, ICON     | • Botones de difusión directa: WhatsApp / Telegram / X         |
+---------------------------------------------------------------------------------------------------+
```

---

## 7. Endpoints API REST y Streaming WebSockets (`app/api/`)

```
+-----------------------------------+--------------------+-------------------------------------------+
| ENDPOINT                          | MÉTODO / PROTOCOLO | FUNCIÓN / RETORNO                         |
+-----------------------------------+--------------------+-------------------------------------------+
| /ws/telemetry/live                | WebSocket          | Stream en tiempo real de telemetría (1 Hz)|
| /api/v1/dashboard/overview        | GET                | Estado consolidado actual de la estación  |
| /api/v1/telemetry/history         | GET                | Series históricas agregadas (5m, 1h, 1d)  |
| /api/v1/thermodynamics/sounding   | GET                | Perfil vertical y cálculo Skew-T MetPy    |
| /api/v1/forecast/ensemble-bands   | GET                | Cuantiles p10-p50-p90 del Super-Ensamble  |
| /api/v1/radar/frames              | GET                | GeoJSON / Imágenes PNG del Nowcasting     |
| /api/v1/knowledge/query           | POST               | Consulta GraphRAG Graphify para LLMs      |
| /api/v1/alerts/publish            | POST               | Emisión manual/automática a redes sociales|
+-----------------------------------+--------------------+-------------------------------------------+
```

---

## 8. Implementación Referencial del Backend, WebSockets y Graphify

### 8.1. Esquemas de Datos Pydantic v2 (`schemas.py`)

```python
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class SensorQualityControl(BaseModel):
    is_valid: bool = True
    temp_zscore: float = 0.0
    pressure_jump_flag: bool = False


class TelemetryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    station_id: str = "XAL-CENTRO-01"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    temperature_c: float = Field(..., ge=-40.0, le=60.0)
    humidity_pct: float = Field(..., ge=0.0, le=100.0)
    pressure_hpa: float = Field(..., ge=700.0, le=1100.0)
    rain_rate_mmh: float = Field(default=0.0, ge=0.0)
    rain_accum_24h_mm: float = Field(default=0.0, ge=0.0)
    wind_speed_kmh: float = Field(default=0.0, ge=0.0)
    wind_gust_kmh: float = Field(default=0.0, ge=0.0)
    wind_direction_deg: float = Field(default=0.0, ge=0.0, le=360.0)
    battery_v: float = Field(default=4.15, ge=3.0, le=4.5)
    qc: SensorQualityControl = Field(default_factory=SensorQualityControl)


class ThermodynamicIndices(BaseModel):
    dewpoint_c: float
    cape_jkg: float
    cin_jkg: float
    lifted_index: float
    pwat_mm: float
    lcl_hpa: float
    lfc_hpa: Optional[float] = None
    thermal_anomaly_c: float
    norte_surge_detected: bool = False


class RiskAssessment(BaseModel):
    alert_level: Literal["VERDE", "AMARILLO", "NARANJA", "ROJO"]
    dominant_hazard: Literal["NINGUNO", "LLUVIA_TORRENCIAL", "VIENTO_NORTE", "NIEBLA_CERO_VIS", "INUNDACION"]
    basin_overflow_prob: float = Field(..., ge=0.0, le=1.0)
    urban_flood_risk: bool
    recommended_actions: List[str]


class DashboardOverview(BaseModel):
    station_info: dict
    current_telemetry: TelemetryData
    thermodynamics: ThermodynamicIndices
    risk: RiskAssessment
    executive_summary: str
    last_update: datetime = Field(default_factory=datetime.utcnow)
```

### 8.2. Servidor FastAPI con WebSockets, FastMCP y Graphify (`main.py`)

```python
import asyncio
import json
import subprocess
from datetime import datetime
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from schemas import DashboardOverview, TelemetryData, ThermodynamicIndices, RiskAssessment

mcp = FastMCP("IvekBot-Weather-Tools")
app = FastAPI(title="IvekBot Weather Platform API", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message, default=str))
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws/telemetry/live")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/v1/knowledge/query")
async def query_knowledge_graph(payload: dict):
    """Permite al LLM consultar el grafo Graphify con límite de tokens."""
    question = payload.get("question", "")
    budget = payload.get("budget", 1500)
    try:
        cmd = ["graphify", "query", question, "--budget", str(budget)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"result": res.stdout if res.returncode == 0 else res.stderr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dashboard/overview", response_model=DashboardOverview)
async def get_dashboard_overview():
    telemetry = TelemetryData(
        temperature_c=24.5,
        humidity_pct=86.0,
        pressure_hpa=861.2,
        rain_rate_mmh=2.5,
        rain_accum_24h_mm=18.0,
        wind_speed_kmh=16.0,
        wind_gust_kmh=28.0,
        wind_direction_deg=65.0
    )
    thermo = ThermodynamicIndices(
        dewpoint_c=22.0,
        cape_jkg=1850.0,
        cin_jkg=-35.0,
        lifted_index=-4.2,
        pwat_mm=42.5,
        lcl_hpa=890.0,
        lfc_hpa=830.0,
        thermal_anomaly_c=2.1,
        norte_surge_detected=False
    )
    risk = RiskAssessment(
        alert_level="AMARILLO",
        dominant_hazard="LLUVIA_TORRENCIAL",
        basin_overflow_prob=0.28,
        urban_flood_risk=True,
        recommended_actions=[
            "Monitoreo de vados y pasos a desnivel en Xalapa",
            "Manejar con luces encendidas por bancos de niebla vespertinos"
        ]
    )
    return DashboardOverview(
        station_info={"name": "Estación Central Xalapa", "coords": [19.54, -96.92], "elevation_m": 1420},
        current_telemetry=telemetry,
        thermodynamics=thermo,
        risk=risk,
        executive_summary="Ambiente húmedo con alta inestabilidad térmica. Se prevén tormentas dispersas."
    )
```

---

## 9. Frontend Referencial del Dashboard (HTML5 + WebSockets + ECharts)

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>IvekBot Weather Station — Real-Time Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
  <style>
    :root {
      --bg-dark: #0f172a;
      --card-bg: #1e293b;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent-blue: #38bdf8;
      --alert-yellow: #facc15;
      --border-color: #334155;
    }
    body {
      margin: 0;
      background: var(--bg-dark);
      color: var(--text-main);
      font-family: system-ui, -apple-system, sans-serif;
      padding: 16px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border-color);
    }
    .badge {
      background: var(--alert-yellow);
      color: #000;
      font-weight: bold;
      padding: 6px 14px;
      border-radius: 999px;
    }
    .grid-metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin: 16px 0;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 16px;
    }
    .card-title {
      font-size: 0.85rem;
      color: var(--text-muted);
      text-transform: uppercase;
    }
    .card-value {
      font-size: 1.8rem;
      font-weight: 700;
      margin-top: 6px;
      color: var(--accent-blue);
    }
    .charts-container {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
    }
    .chart-box {
      height: 380px;
    }
  </style>
</head>
<body>

  <div class="header">
    <div>
      <h1 style="margin: 0; font-size: 1.5rem;">IvekBot Weather Station — Xalapa</h1>
      <span style="color: var(--text-muted); font-size: 0.9rem;" id="conn-status">Conectando a WebSocket...</span>
    </div>
    <div class="badge" id="alert-badge">ALERTA: AMARILLO</div>
  </div>

  <div class="grid-metrics">
    <div class="card">
      <div class="card-title">Temperatura</div>
      <div class="card-value" id="val-temp">-- °C</div>
    </div>
    <div class="card">
      <div class="card-title">Humedad Relativa</div>
      <div class="card-value" id="val-humidity">-- %</div>
    </div>
    <div class="card">
      <div class="card-title">Presión Barométrica</div>
      <div class="card-value" id="val-pressure">-- hPa</div>
    </div>
    <div class="card">
      <div class="card-title">Viento / Racha</div>
      <div class="card-value" id="val-wind">-- km/h</div>
    </div>
    <div class="card">
      <div class="card-title">Inestabilidad (CAPE)</div>
      <div class="card-value" id="val-cape">-- J/kg</div>
    </div>
  </div>

  <div class="charts-container">
    <div class="card chart-box" id="timeSeriesChart"></div>
    <div class="card chart-box" id="thermoGaugeChart"></div>
  </div>

  <script>
    const timeChart = echarts.init(document.getElementById('timeSeriesChart'));
    const gaugeChart = echarts.init(document.getElementById('thermoGaugeChart'));

    const timeOption = {
      title: { text: 'Tendencia en Tiempo Real (24h)', textStyle: { color: '#f8fafc' } },
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: ['12:00', '13:00', '14:00', '15:00', '16:00'], axisLine: { lineStyle: { color: '#94a3b8' } } },
      yAxis: { type: 'value', axisLine: { lineStyle: { color: '#94a3b8' } }, splitLine: { lineStyle: { color: '#334155' } } },
      series: [
        { name: 'Temperatura (°C)', type: 'line', smooth: true, data: [21.0, 22.5, 24.8, 25.1, 24.5], lineStyle: { color: '#38bdf8' } },
        { name: 'Humedad (%)', type: 'line', smooth: true, data: [90, 85, 78, 75, 86], lineStyle: { color: '#34d399' } }
      ]
    };
    timeChart.setOption(timeOption);

    const gaugeOption = {
      title: { text: 'Índice de Convección (CAPE)', textStyle: { color: '#f8fafc' } },
      series: [{
        type: 'gauge',
        max: 3000,
        progress: { show: true },
        detail: { valueAnimation: true, formatter: '{value} J/kg', color: '#f8fafc', fontSize: 16 },
        data: [{ value: 1850, name: 'CAPE' }]
      }]
    };
    gaugeChart.setOption(gaugeOption);

    const ws = new WebSocket(`ws://${location.host || 'localhost:8000'}/ws/telemetry/live`);
    ws.onopen = () => {
      document.getElementById('conn-status').innerText = '🟢 Transmisión en Vivo Conectada';
      document.getElementById('conn-status').style.color = '#34d399';
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.temperature_c !== undefined) {
        document.getElementById('val-temp').innerText = `${data.temperature_c} °C`;
        document.getElementById('val-humidity').innerText = `${data.humidity_pct} %`;
        document.getElementById('val-pressure').innerText = `${data.pressure_hpa} hPa`;
        document.getElementById('val-wind').innerText = `${data.wind_speed_kmh} km/h`;
      }
    };
  </script>
</body>
</html>
```

---

## 10. Firmware Referencial del Sensor IoT ESP32 (MicroPython / MQTT)

```python
import time
import ujson
import network
from umqtt.simple import MQTTClient

WIFI_SSID = "Meteorologia_Net"
WIFI_PASS = "ClaveSegura2026"
MQTT_BROKER = "192.168.1.100"
STATION_ID = "XAL-CENTRO-01"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.5)

def run_sensor_loop():
    connect_wifi()
    client = MQTTClient(STATION_ID, MQTT_BROKER, port=1883)
    client.connect()

    while True:
        try:
            payload = {
                "station_id": STATION_ID,
                "temperature_c": 24.5,
                "humidity_pct": 86.0,
                "pressure_hpa": 861.2,
                "rain_rate_mmh": 0.0,
                "wind_speed_kmh": 14.5,
                "battery_v": 4.18
            }
            client.publish("telemetry/xalapa", ujson.dumps(payload), qos=1)
        except Exception as e:
            connect_wifi()
        time.sleep(5)
```

---

## 11. Esquema de Base de Datos TimescaleDB (DDL)

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS sensor_telemetry (
    time TIMESTAMPTZ NOT NULL,
    station_id VARCHAR(32) NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    humidity_pct DOUBLE PRECISION NOT NULL,
    pressure_hpa DOUBLE PRECISION NOT NULL,
    rain_rate_mmh DOUBLE PRECISION DEFAULT 0.0,
    wind_speed_kmh DOUBLE PRECISION DEFAULT 0.0,
    wind_direction_deg DOUBLE PRECISION DEFAULT 0.0,
    battery_v DOUBLE PRECISION DEFAULT 4.2,
    qc_valid BOOLEAN DEFAULT TRUE
);

SELECT create_hypertable('sensor_telemetry', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);

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
```

---

## 12. Despliegue de Producción con Docker Compose

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
