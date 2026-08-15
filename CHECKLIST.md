# ✅ Checklist de Avance — IvekBot Weather Station

> **Última actualización:** 2026-08-15 · **Commit ancla:** `f9b0d4a` · **Rama:** `main` → `origin/main`
> **PDF:** `estscionmeteorologica.pdf` es **HISTÓRICO** (dump previo al recorte 750→179 líneas de `estacion_meteorologica.md 1.3.0`). No regenerar hasta re-exportar la memoria. Sin impacto en demo.
> **Auditoría base:** `AUDITORIA_GAPS_DOCUMENTACION.md` (2026-08-14, base `3d8829b`, histórico) · **Docs reescritos:** `README 1.3.0` + `SDD 1.2.0` + `memoria 1.3.0` (ancla `1513c19`)
> **Para el próximo agente:** lee primero `README.md` + `SDD.md` + `estacion_meteorologica.md` (los 3 con front-matter `1513c19`), luego este checklist y la auditoría histórica.

## Cómo usar este checklist

1. Elige la siguiente tarea `[ ]` por prioridad (P0 → P1 → P2).
2. Haz el cambio, verifica (`python -m py_compile`, `git diff --stat`), marca `[x]` aquí y commitea con mensaje `feat/fix/docs: ...`.
3. Haz `git push` al terminar cada bloque P0/P1.
4. Si necesitas razonamiento ML pesado (P2), usa inteligencia superior; para P0/P1 basta media/económica.

---

## ✅ Completado — Verificado en código (no perder)

### Docs reescritos — ancla `1513c19` (2026-08-15)

- [x] **README.md 1.3.0 (AS-IS)** — reescritura completa: sin badge MIT, sin `1 Hz`/`sub-segundo`, sin SA1-SA6 como clases; quick start uvicorn + simulador + URL; tabla estado AS-IS vs TO-BE; endpoints reales (7); LLM solo `executive_summary`/`public_bulletin`; front-matter `1513c19`.
- [x] **SDD.md 1.2.0 (HÍBRIDO)** — C4 dual AS-IS/TO-BE, §4 contratos reales (`WeatherOrchestrator`, `compute_atmospheric_physics`, `assess_basin_hydrology_risk`, `query_graphify_knowledge`), §4bis roles TO-BE, Norte dual (`physics_engine.py:85` vs dominio), §8/§9 por referencia a `init.sql`/`docker-compose.yml`.
- [x] **estacion_meteorologica.md 1.3.0 (HÍBRIDO)** — recorte 750→179 líneas; borrados dumps Python/HTML/SQL/YAML; conservados §2 y §2.1 íntegros + recuadro dominio vs código; front-matter `1513c19`. Cero tercera jerarquía de agentes.
- [x] **Grep de rechazo** — `1 Hz`/`License: MIT`/clases SA* como AS-IS en cero en los 3 MD de producto (solo menciones TO-BE/reglas anti-claim).

### Docs corregidos — commit `30f703e` (2026-08-14) — base histórica

- [x] **README.md** — quitados claims falsos (6 subagentes → 1 orquestador + 4 tools; sub-segundo → 2 s/0.5 Hz; Z-Score/AKF → validación simple; p10/p90 multi-modelo → sintético; matview → TO-BE). Añadida tabla 6 vars efectivas + nota `python-dotenv` + endpoints reales (6) + limitaciones.
- [x] **.env.example** — `LLM_PROVIDER` marcado etiqueta informativa; `DATABASE_URL/REDIS_URL/MQTT_*/GRAPHIFY/ENV/PORT/HOST` marcados TO-BE; `MAX_TOKENS/TEMPERATURE` ajustados a valores reales (250/300/0.3) y documentados como SÍ efectivos.
- [x] **requirements.txt** — añadido `python-dotenv>=1.0.0`.
- [x] **app/agents/orchestrator.py** — añadido `load_dotenv()` + `ORCHESTRATOR_MAX_TOKENS/TEMPERATURE` y `RISK_*` leídos del `.env`.
- [x] **docker-compose.yml** — `env_file: .env`, volúmenes acotados, `healthcheck` del app.
- [x] **SDD.md v1.2.0** — banner AS-IS vs TO-BE; §2.1/§2.2 corregidos; §3 vars corregidas; §4 tabla ESTADO; §5 solo `query` AS-IS.
- [x] **Auditoría** — `AUDITORIA_GAPS_DOCUMENTACION.md` commiteada como histórico base.

### Código AS-IS que SÍ funciona (1,363 LOC reales)

- [x] FastAPI 3.5.0 (`app/main.py:27`) + 7 rutas + `WS /ws/telemetry/live` cada 2 s (`asyncio.sleep(2)` L107) + CORS + `static/index.html`.
- [x] `WeatherOrchestrator` + 4 tools FastMCP (`mcp_server.py` 4× `@mcp.tool`) + `physics_engine.py` (MetPy opcional con fallback Magnus-Tetens/Espy) + `schemas.py` (`extra=ignore`).
- [x] Semáforo 4 niveles + `assess_basin_hydrology_risk` con umbrales reales (`mcp_server.py:46-96`).
- [x] Gateway agnóstico OpenAI-compatible (`orchestrator.py:32-61`, `POST {base}/chat/completions`, fallback determinista sin key).
- [x] Dashboard `static/` (5 tarjetas, gauge CAPE 0-3500, ECharts 24h, abanico sintético p50/p90).
- [x] Firmware ESP32 (`firmware/esp32_sensor_node.py` 91L, MQTT QoS 1, batería/IRQ) + `simulator/sensor_simulator.py` 51L + `database/init.sql` 51L (3 tablas, hypertable).
- [x] `graphify-out/` generado + `build_graph.py` 56L (`--budget 1500`).
- [x] **Prompt caching + dedup LLM** (`ab24d0f`) — `SYSTEM_*_STATIC` cacheables con `cache_control: ephemeral` + dedup local TTL 60s.

---

## ⏳ Pendiente — Priorizado (TO-BE honesto)

### P0 — Bloquea cierre documental

- [x] **P0.0 Cierre git** — `f9b0d4a` pusheado: `README 1.3.0` + `SDD 1.2.0` + `memoria 1.3.0` ancla `1513c19`.
- [ ] **P0.1 Decisión LICENSE** — añadir `LICENSE` real o dejar sin licencia (README ya sin badge; no inventar MIT).
- [x] **P0.2 PDF histórico** — `estscionmeteorologica.pdf` queda como **HISTÓRICO** en la raíz (desfasado del md 1.3.0 recortado; no regenerar ahora). Ver nota en CHECKLIST §PDF.

### P1 — Deuda docs/código menor (1-2h, DeepSeek Flash basta)

- [x] **P1.1 Persistencia honesta** — ya documentado como TO-BE (README/SDD §8). SDD ya dice "vista continua no en SQL" + tabla Estado AS-IS vs TO-BE. Init.sql mantiene 3 tablas + CAGG TO-BE comentada.
- [x] **P1.2 `requests` faltante** — añadido `requests>=2.31.0` a `requirements.txt` con comentario "solo para simulator".
- [x] **P1.3 Sincronizar DDL** — `telemetry_5min` añadida como bloque comentado TO-BE en `database/init.sql` §4; `forecast_verification_log`/`weather_alerts` siguen en SQL sin escritor (SDD §8 ya lo declara).

### P2 — ML avanzado (reservar inteligencia superior, solo con datos)

- [ ] **P2.1 Super-ensamble LightGBM cuantílico** — hoy sintético (`orchestrator.py:163-189`).
- [ ] **P2.2 Nowcasting pysteps + GOES-16** — flujo Lucas-Kanade, Banda 13 IR + GLM.
- [ ] **P2.3 Verificación CRPS/CSI + EMA closed-loop** — `forecast_verification_log` + recalibración.
- [ ] **P2.4 Downscaling / S2S MJO/CAMS/ERA5** — solo cuando P0/P1 cerrados.

---

## 📋 Para el próximo agente — checklist de mano

- [ ] Leer `README.md` + `SDD.md` + `estacion_meteorologica.md` (front-matter `1513c19`) y luego este archivo.
- [ ] Elegir siguiente `[ ]` de P0, implementar, `python -m py_compile`, `git diff --stat`, marcar `[x]` aquí, `git commit` + `git push`.
- [ ] No regenerar `graph.json`/`GRAPH_REPORT.md` como "avance" (son generados).
- [ ] No reintroducir claims falsos; respetar AS-IS vs TO-BE.

## 💰 Nota sobre uso de LLMs

- **P0/P1 → DeepSeek V4 Flash** (suficiente, 1/3 costo, sin alucinar docs).
- **P2 → GPT 5.6 Luna / Grok 4.6 / GLM 5.3** — razonamiento pesado solo con datos históricos reales.

---

## 📜 Historial de commits

- `1513c19` (2026-08-15) — docs: reescritura README 1.3.0 + SDD 1.2.0 + memoria 1.3.0 ANCLA AS-IS vs TO-BE (543+ / 1076- líneas)
- `30f703e` (2026-08-14) — docs: corregir 4 MD post-auditoría AS-IS vs TO-BE + dotenv + compose
- `ab24d0f` (2026-08-14) — feat(llm): prompt caching + dedup
- `3d8829b` — feat: gateway provider-agnostic
