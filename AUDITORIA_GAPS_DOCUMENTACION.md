# Auditoría de Gaps Documentales — IvekBot Weather Station

> Estado: ENTREGABLE DE INVESTIGACIÓN (research-lead). No modifica los MD existentes.
> Fecha de consulta: 2026-08-14 · Último commit conocido: 3d8829b (provider-agnostic gateway).
> Método: lectura directa de 20 archivos + verificación cruzada claim↔código (archivo:línea). Claim sin respaldo en código ni en MD = marcado **sin evidencia**. Confianza: ALTA (lectura directa), MEDIA (interpretación), BAJA (fuente externa).

## 0. Resumen ejecutivo (top hallazgos)

1. **README afirma capacidades que el código no tiene**: seis subagentes, Modified Z-Score, vistas materializadas continuas, transmisión sub-segundo (el loop emite cada 2 s), abanico p10/p50/p90 (el frontend solo grafica p50/p90). Un LLM que lea solo README inferirá módulos inexistentes.
2. **El paso de configuración del README no funciona**: cp .env.example .env NO surte efecto porque ningún módulo lee .env (no hay python-dotenv en requirements; app/agents/orchestrator.py usa os.getenv directo). De las 16 variables del .env.example, el código lee solo 4: LLM_BASE_URL, LLM_API_KEY, ORCHESTRATOR_MODEL, RISK_AGENT_MODEL.
3. **estacion_meteorologica.md es ~85% dump duplicado y desfasado**: schemas (extra=forbid vs ignore real), main.py (version 3.1.0 vs 3.5.0 real; overview hardcodeado vs pipeline real), HTML, firmware y SQL antiguos. Es el principal foco de contaminación para un LLM.
4. **Fórmulas regionales de Xalapa valiosas pero NO implementadas**: Norte (deltaP3h, deltaT3h), convección severa (CAPE>=1800, CIN>=-40, PWAT>=40, LI<=-3.0) y niebla orográfica (T-Td<=0.8, LCL<=1450) existen solo en la memoria. El código implementa una aproximación distinta del Norte (umbrales absolutos) y nada de niebla.
5. **SDD cita IEEE 1016-2009 pero le faltan**: ADRs, requisitos, seguridad, observabilidad, pruebas, criterios de aceptación y versionado. Mezcla spec con implementación sin marcar AS-IS vs TO-BE.
6. **El DDL documentado no coincide con database/init.sql**: la vista materializada telemetry_5min está en SDD sección 8 y memoria sección 11 pero NO en init.sql; forecast_verification_log y weather_alerts están en init.sql pero NO en los docs.
7. **El docker-compose documentado (SDD sección 9) no coincide con el real**: el real no inyecta LLM_* al contenedor (dentro de Docker el gateway nunca tendrá API key), y el real monta .:/app (volumen) que el SDD omite.
8. **GRAPH_REPORT es una salida generada (regenerable)**: no nombra comunidades (solo Community 0..8); la memoria les asigna nombres (ej. Comunidad 1: Protocolos de Inundación) que NO están en el reporte → etiquetas sin evidencia. THEME aparece aislado por falso negativo del extractor (sí se usa en dashboard.js).
9. **Sin observabilidad ni pruebas**: no hay /health, no hay logging estructurado, no hay carpeta tests/, no hay CI. El compose define healthchecks solo para timescaledb y redis.
10. **No hay nada de Django**: el proyecto es FastAPI puro. La carpeta padre se llama django/ pero no hay manage.py ni settings.py. Ningún MD debe afirmar Django.

## 1. Inventario de claims por documento

Leyenda: ✅ Implementado · 🟡 Parcial · 📝 Solo spec (en docs, no en código) · ❌ Contradicho (doc vs código/doc).

### 1.1 README.md

| Claim (cita) | Estado | Evidencia / Contraevidencia |
|---|---|---|
| Núcleo físico MetPy: CAPE, CIN, PWAT, LCL, LFC, Nortes a $0 tokens (L18) | 🟡 | physics_engine.py usa MetPy opcional con fallback heurístico; CAPE/CIN/PWAT/LCL/LFC son estimaciones; Norte implementado con umbrales absolutos (physics L50-99) |
| Orquestación Multi-Agente FastMCP: 6 subagentes + orquestador master (L19) | 📝 | No existen clases SA1-SA6. Solo WeatherOrchestrator (agents/orchestrator.py) y 4 tools FastMCP (mcp_server.py L11-111) |
| LLM Gateway agnóstico (OpenAI-compatible) (L20) | ✅ | _call_llm genérico con fallback (orchestrator L32-61); README L57: sin key funciona con plantillas |
| GraphRAG Graphify --budget 1500 (L21) | ✅ | build_graph.py usa graphify.detect/extract/build/cluster; budget 1500 en .env L41 y defaults schemas L91 |
| WebSockets sub-segundo /ws/telemetry/live (L22) | ❌ | El loop emite cada **2 s** (asyncio.sleep(2), main L107) → 0.5 Hz, no sub-segundo ni 1 Hz (SDD L210 dice 1 Hz) |
| Abanico probabilístico 14 días p10/p50/p90 (L22) | 🟡 | ensemble_14d existe (orchestrator L163-189) pero es **sintético** (fórmulas pseudoaleatorias, no multi-modelo); frontend solo grafica p50/p90 (dashboard.js L205-206) |
| ESP32 MQTT QoS 1 + QC Modified Z-Score (L23) | 🟡 | QoS 1 sí (firmware L83). Modified Z-Score: **sin evidencia**; QC real es validación simple (mcp_server L16-19); SensorQualityControl tiene campos sin cálculo |
| TimescaleDB hypertables + vistas materializadas continuas 5 min (L24) | 🟡 | Hypertable sí (init.sql L21-26). La matview telemetry_5min **no está en init.sql** (solo en SDD §8 / memoria §11) |
| cp .env.example .env y listo (L30-33) | ❌ | Ningún módulo lee .env (sin python-dotenv en requirements). Solo 4 de 16 variables se leen por os.getenv (orchestrator L27-30) |
| Sin API key el sistema funciona 100% (L57) | 🟡 | Cierto para síntesis (fallbacks orchestrator L125-161). No aplica a Graphify CLI ausente ni a otras rutas |
| pip install -r requirements.txt (L65) | 🟡 | Funciona, pero el simulador necesita requests (no está en requirements) y el flujo .env necesita dotenv |
| uvicorn app.main:app --reload ... → http://localhost:8000 (L70-72) | ✅ | Comando válido; / sirve static/index.html (main L191-193) |
| docker compose up -d --build (L76) | 🟡 | Compose válido, pero no inyecta LLM_* (dentro de Docker no hay key) y no hay healthcheck del app |

**README NO documenta** (confirmado): simulador, firmware, build_graph.py, healthchecks, endpoints reales, degradación elegante paso a paso, límites conocidos (ensamble sintético, sin difusión real, sin Kalman/pysteps/LightGBM).

### 1.2 .env.example

| Claim (cita) | Estado | Evidencia / Contraevidencia |
|---|---|---|
| ENVIRONMENT, PORT, HOST (L6-8) | 📝 | Ningún módulo lee estas variables. Sin evidencia de uso |
| LLM_PROVIDER, LLM_BASE_URL, LLM_API_KEY (L16-18) | 🟡 | LLM_BASE_URL y LLM_API_KEY sí (orchestrator L27-28). LLM_PROVIDER **no se lee** |
| ORCHESTRATOR_MODEL, ORCHESTRATOR_MAX_TOKENS, ORCHESTRATOR_TEMPERATURE (L21-23) | 🟡 | ORCHESTRATOR_MODEL sí (orchestrator L29). MAX_TOKENS y TEMPERATURE **no se leen** (el código hardcodea max_tokens=250/300 y temperature=0.3, orchestrator L49-50) |
| RISK_AGENT_MODEL, RISK_AGENT_MAX_TOKENS, RISK_AGENT_TEMPERATURE (L26-28) | 🟡 | RISK_AGENT_MODEL sí (orchestrator L30). MAX_TOKENS y TEMPERATURE **no se leen** |
| DATABASE_URL, REDIS_URL (L33-34) | 📝 | **Sin evidencia**: ningún módulo importa asyncpg/psycopg2/redis en app/. El código corre 100% en memoria |
| MQTT_BROKER_HOST, MQTT_BROKER_PORT (L35-36) | 📝 | **Sin evidencia**: no hay suscriptor MQTT en el repo; el firmware publica, la app no consume |
| GRAPHIFY_TOKEN_BUDGET (L41) | 📝 | No se lee en build_graph.py (usa constantes) ni en mcp_server.py (default 1500 hardcodeado) |

### 1.3 SDD.md

| Claim (cita) | Estado | Evidencia / Contraevidencia |
|---|---|---|
| Estándar IEEE 1016-2009 (L7) | 🟡 | El doc cita el estándar pero no implementa sus vistas completas (ver sección 5: huecos SDD) |
| Ubicación Xalapa 19.54N 96.92W 1420 msnm (L8) | ✅ | Consistente con main L149-150 y index.html L18 |
| Separación estricta determinista vs cognitivo (L18-20) | ✅ | compute_atmospheric_physics y assess_basin_hydrology_risk son deterministas; LLM solo en síntesis (orchestrator) |
| Pasarela LLM agnóstica OpenAI-compatible (L21-22) | ✅ | orchestrator _call_llm usa /chat/completions (L37) |
| GraphRAG con comunidades Louvain, --budget 1500 (L23-24) | ✅ | build_graph.py cluster() con Louvain (graphify); budget 1500 default |
| Resiliencia: sin API key conmuta a motores deterministas (L25-26) | ✅ | Fallbacks en orchestrator L125-161 |
| Tabla Fase Desarrollo/Operación (L34-44) | 🟡 | Operación describe ingesta 1 Hz, pysteps radar, alertas ciudadanas que **no existen en código** |
| C4: ESP32 → MQTT → SA1 ... SA6 (L46-107) | 📝 | SA1-SA6 no existen como módulos; MQTT broker no se consume; REDIS no se usa; LLM_GW conecta solo vía orchestrator |
| Tabla proveedores/modelos (L115-126) | 🟡 | Base URLs correctas; modelos son sugerencias (gpt-4o-mini default en orchestrator) |
| Variables .env del SDD (L128-143) | ❌ | Incluye ORCHESTRATOR_MAX_TOKENS, ORCHESTRATOR_TEMPERATURE, RISK_AGENT_* que **no se leen**; omite que solo 4 variables tienen efecto |
| Tabla de 7 subagentes (ORQ, SA1-SA6, KG) (L149-162) | 📝 | No existe implementación por subagente; solo 4 tools MCP y un orquestador |
| SA1: Modified Z-Score |M_i|>3.5 + AKF (L169-172) | 📝 | **Sin evidencia en código**; QC real: if temp>45 o hum>100 → invalid (mcp_server L16-19) |
| SA2: Norte ΔP3h>=+2.5 hPa ∧ Dir∈[300,360] ∧ Racha>=50 ∧ ΔT3h<=-4.0 (L176) | 📝 | **Spec regional**: el código usa umbrales absolutos (P>864, T<18, dir 300-360 o <=30, physics L85) — no usa deltas temporales |
| SA3: Lucas-Kanade pysteps, GOES-16 Banda 13 (L178-179) | 📝 | **Sin evidencia** (no hay pysteps en requirements ni código) |
| SA4: ECMWF/GFS/ICON/HRRR + LightGBM cuantiles (L181-183) | 📝 | **Sin evidencia** (no hay LightGBM en requirements; el ensamble es sintético) |
| SA5: MAE, RMSE, CRPS, CSI + EMA (L185-187) | 📝 | **Sin evidencia** (forecast_verification_log existe en SQL pero nadie lo escribe) |
| SA6: Cuencas Actopan/La Antigua/Sordo + semáforo 4 niveles (L189-192) | 🟡 | Semáforo VERDE/AMARILLO/NARANJA/ROJO y umbrales sí en mcp_server L46-96. Nombres de cuencas: solo en docstring/acciones de texto (L44, L67), no como modelo de datos |
| Graphify tools graphify_query/find_path/explain (L199-204) | 🟡 | Solo query_graphify_knowledge existe (mcp_server L100-111). find_path/explain **no existen** |
| Dashboard: 5 tarjetas, gauge CAPE 0-3500, abanico 14d, visor alertas + caja Graphify (L210-216) | ✅ | index.html y dashboard.js implementan: 5 tarjetas, gauge max 3500 (L104), alert badge, graphify box |
| Hardware: BME280 GPIO4 pluviómetro GPIO5 anemómetro GPIO34 batería (L222-223) | ✅ | firmware L22-24 coincide |
| DDL TimescaleDB con matview telemetry_5min (L230-265) | ❌ | init.sql NO incluye telemetry_5min; SDD omite forecast_verification_log y weather_alerts (init.sql L29-51) |
| Docker Compose con env LLM_* e healthchecks (L271-343) | ❌ | El compose real (docker-compose.yml) NO inyecta LLM_* ni OPEN_METEO_API al servicio; el SDD muestra variables que el real omite |
| Endpoint 1 Hz /ws/telemetry/live (L210) | ❌ | Loop real cada 2 s (main L107) |

### 1.4 estacion_meteorologica.md (memoria técnica)

| Claim (cita) | Estado | Evidencia / Contraevidencia |
|---|---|---|
| Estado del arte: Nowcasting 0-6h pysteps/GOES-16, Corto/Medio ECMWF/GFS/ICON/HRRR, S2S MJO/CAMS/ERA5 (L36-48) | 📝 | Metodología de referencia, **sin implementación en el repo** (sin pysteps, sin GOES, sin CAMS, sin MJO) |
| Norte: ΔP3h>=+2.5, giro 330-360, rachas>=50, ΔT3h<=-4.0 (L52-53) | 📝 | **Spec regional valiosa**; el código implementa variante con umbrales absolutos (physics L85) — NO coincide |
| Convección severa: CAPE>=1800, CIN>=-40, PWAT>=40, LI<=-3.0 (L54-55) | 📝 | **Spec regional valiosa**; no hay lógica de activación por estos umbrales en código |
| Niebla orográfica: T-Td<=0.8 y LCL<=1450 msnm (L56-57) | 📝 | **Spec regional valiosa**; sin implementación (no existe NIEBLA en el motor de riesgo salvo mención en acciones, mcp_server L86) |
| Graphify reduce tokens --budget 1500 (L66) | ✅ | build_graph.py y defaults lo soportan |
| Comunidades nombradas: Comunidad 1: Protocolos de Inundación Cuenca Actopan-La Antigua; Comunidad 2: Física MetPy; Comunidad 3: Pipeline MQTT (L67) | ❌ | GRAPH_REPORT solo etiqueta Community 0..8 (GRAPH_REPORT L51-77). Los nombres de la memoria **no están en el reporte generado** → sin evidencia |
| Diagrama [Sensor Presión BME280] → [TelemetryData] → [Detección Norte] → [Alerta Naranja] (L70-76) | 🟡 | Nodos existen pero las relaciones EMITE_LECTURA/ASIMILADO_POR/DISPARA_PROTOCOLO son inventadas (el grafo real no usa esas etiquetas) |
| Tools graphify_query/find_path/explain (L82-108) | 🟡 | Solo query existe (mcp_server L100-111) |
| Flujo de datos: A1-A4, SA1-SA5, KG, REDIS, AUD (L114-183) | 📝 | Arquitectura objetivo; REDIS/AUD/SA4/SA5 no existen en código |
| Jerarquía de subagentes SA1-SA5 (L189-199) | 📝 | No existen como módulos |
| Dashboard referencial 6 paneles: mapa radar, skew-T, Leaflet, difusión social (L205-226) | 📝 | El dashboard real (index.html) NO tiene mapa radar, ni skew-T, ni Leaflet, ni botones de difusión |
| Endpoints: /history, /thermodynamics/sounding, /forecast/ensemble-bands, /radar/frames, /alerts/publish (L236-244) | ❌ | **No existen** en app/main.py. Solo: GET /dashboard/overview, GET /forecast/report, POST /telemetry/ingest, POST /knowledge/query, WS /ws/telemetry/live, GET / |
| Schemas Pydantic con extra=forbid (L266) | ❌ | Real: extra=ignore (schemas L15) |
| main.py version 3.1.0, overview hardcodeado (L325, L381-420) | ❌ | Real: version 3.5.0 (main L27) y overview construido desde pipeline (main L142-158) |
| Firmware referencial sin batería/IRQ (L589-628) | ❌ | El firmware real es más completo (batería L44-50, IRQ L54-55, QoS L83); el dump de la memoria está desfasado |
| DDL con matview telemetry_5min (L652-667) | ❌ | No está en init.sql |
| Docker Compose (L673-739) | ❌ | Igual desfase que SDD: el real no inyecta LLM_* |
