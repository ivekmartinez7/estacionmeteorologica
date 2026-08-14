# Graph Report - estacionMeteorologica  (2026-08-14)

## Corpus Check
- Corpus is ~7,788 words - fits in a single context window. You may not need a graph.

## Summary
- 86 nodes · 163 edges · 12 communities (10 shown, 2 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10

## God Nodes (most connected - your core abstractions)
1. `WeatherOrchestrator` - 13 edges
2. `TelemetryData` - 12 edges
3. `compute_atmospheric_physics()` - 11 edges
4. `ThermodynamicIndices` - 11 edges
5. `RiskAssessment` - 11 edges
6. `assess_basin_hydrology_risk()` - 7 edges
7. `ForecastReport` - 7 edges
8. `ConnectionManager` - 6 edges
9. `EnsembleForecastDay` - 6 edges
10. `ingest_and_validate_telemetry()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `WeatherOrchestrator` --uses--> `EnsembleForecastDay`  [INFERRED]
  app/agents/orchestrator.py → app/schemas.py
- `WeatherOrchestrator` --uses--> `ForecastReport`  [INFERRED]
  app/agents/orchestrator.py → app/schemas.py
- `WeatherOrchestrator` --uses--> `RiskAssessment`  [INFERRED]
  app/agents/orchestrator.py → app/schemas.py
- `WeatherOrchestrator` --uses--> `TelemetryData`  [INFERRED]
  app/agents/orchestrator.py → app/schemas.py
- `ingest_telemetry()` --uses--> `TelemetryData`  [INFERRED]
  app/main.py → app/schemas.py

## Import Cycles
- None detected.

## Communities (12 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.15
Nodes (18): get_dashboard_overview(), get_forecast_report(), ingest_telemetry(), Any, query_knowledge(), Generador en tiempo real de telemetría viva para clientes conectados., serve_dashboard(), simulate_realtime_weather_stream() (+10 more)

### Community 1 - "Community 1"
Cohesion: 0.39
Nodes (5): Ejecuta el ciclo de vida completo del pronóstico: 1. Subagente Ingesta & QC 2.…, Telemetría física de superficie enviada por la estación ESP32., Evaluación de riesgo hidrometeorológico., RiskAssessment, TelemetryData

### Community 2 - "Community 2"
Cohesion: 0.32
Nodes (4): ConnectionManager, Gestiona conexiones activas de WebSockets para dashboards en tiempo real., websocket_endpoint(), WebSocket

### Community 3 - "Community 3"
Cohesion: 0.32
Nodes (7): calculate_dewpoint(), calculate_lcl(), compute_atmospheric_physics(), Any, Calcula el punto de rocío usando la ecuación de Magnus-Tetens., Calcula el Nivel de Condensación por Elevación (LCL en hPa)., Calcula el perfil termodinámico y determinista completo sin intervención de…

### Community 4 - "Community 4"
Cohesion: 0.32
Nodes (7): EnsembleForecastDay, ForecastReport, Pronóstico probabilístico diario del ensamble., Reporte integral consolidado por el Orquestador Multi-Agente., Banderas de control de calidad para datos de sensores físicos., SensorQualityControl, BaseModel

### Community 5 - "Community 5"
Cohesion: 0.36
Nodes (5): connectWebSocket(), loadForecastReport(), loadInitialData(), THEME, updateTelemetryUI()

### Community 6 - "Community 6"
Cohesion: 0.40
Nodes (4): Orquestador Central Multi-Agente para la estación meteorológica., WeatherOrchestrator, Índices de inestabilidad y física atmosférica calculados por MetPy., ThermodynamicIndices

### Community 7 - "Community 7"
Cohesion: 0.40
Nodes (6): calculate_thermodynamics(), ingest_and_validate_telemetry(), Any, Asimila, valida y aplica control de calidad (QC) a los datos de la estación…, Ejecuta el cálculo determinista de termodinámica atmosférica (CAPE, CIN, LCL,…, tool

### Community 8 - "Community 8"
Cohesion: 0.53
Nodes (5): connect_wifi(), main(), rain_interrupt_handler(), Firmware MicroPython para Nodo IoT ESP32 (Estación Meteorológica) Conecta…, read_battery_voltage()

## Knowledge Gaps
- **1 isolated node(s):** `THEME`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `compute_atmospheric_physics()` connect `Community 3` to `Community 0`, `Community 9`, `Community 1`, `Community 7`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `ConnectionManager` connect `Community 2` to `Community 0`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `TelemetryData` connect `Community 1` to `Community 0`, `Community 4`, `Community 6`, `Community 7`, `Community 9`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `WeatherOrchestrator` (e.g. with `EnsembleForecastDay` and `ForecastReport`) actually correct?**
  _`WeatherOrchestrator` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TelemetryData` (e.g. with `WeatherOrchestrator` and `ingest_telemetry()`) actually correct?**
  _`TelemetryData` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `RiskAssessment` (e.g. with `WeatherOrchestrator` and `assess_basin_hydrology_risk()`) actually correct?**
  _`RiskAssessment` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `THEME` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._