# ✅ Checklist de Avance — IvekBot Weather Station

> **Última actualización:** 2026-08-14 · **Commit:** `30f703e` · **Rama:** `main` → `origin/main` (pusheado ✅)
> **Auditoría base:** `AUDITORIA_GAPS_DOCUMENTACION.md` (2026-08-14, 10 hallazgos) · **SDD verificado:** v1.2.0
> **Para el próximo agente:** lee este archivo primero, luego `README.md` + `SDD.md` + `AUDITORIA_GAPS_DOCUMENTACION.md`. Marca `[x]` al terminar cada tarea y commitea.

## Cómo usar este checklist

1. Elige la siguiente tarea `[ ]` por prioridad (P0 → P1 → P2).
2. Haz el cambio, verifica (`python -m py_compile`, `git diff --stat`), marca `[x]` aquí y commitea con mensaje `feat/fix/docs: ...`.
3. Haz `git push` al terminar cada bloque P0/P1.
4. Si necesitas razonamiento ML pesado (P2), usa inteligencia superior (Grok 4.6); para P0/P1 basta media/económica.

---

## ✅ Completado — Verificado en código (no perder)

### Docs corregidos — commit `30f703e` (2026-08-14)

- [x] **README.md** — quitados claims falsos (6 subagentes → 1 orquestador + 4 tools; sub-segundo → 2 s/0.5 Hz; Z-Score/AKF → validación simple; p10/p90 multi-modelo → sintético; matview → TO-BE). Añadida tabla 6 vars efectivas + nota `python-dotenv` + endpoints reales (6) + limitaciones. Verificado.
- [x] **.env.example** — `LLM_PROVIDER` marcado etiqueta informativa; `DATABASE_URL/REDIS_URL/MQTT_*/GRAPHIFY/ENV/PORT/HOST` marcados TO-BE; `MAX_TOKENS/TEMPERATURE` ajustados a valores reales (250/300/0.3) y documentados como SÍ efectivos.
- [x] **requirements.txt** — añadido `python-dotenv>=1.0.0`.
- [x] **app/agents/orchestrator.py** — añadido `load_dotenv()` + `ORCHESTRATOR_MAX_TOKENS/TEMPERATURE` y `RISK_*` leídos del `.env` (antes hardcodeados 250/300/0.3). `_call_llm` ahora recibe `temperature` param.
- [x] **docker-compose.yml** — `env_file: .env` para inyectar `LLM_*` al contenedor; volúmenes acotados `./app:/app/app:ro` + `./static:/app/static:ro`; `healthcheck` del app añadido. Ya no monta `.:/app` genérico.
- [x] **SDD.md v1.2.0** — banner AS-IS vs TO-BE; §2.1 tabla desdoblada AS-IS/TO-BE; §2.2 nota AS-IS/TO-BE; §3 vars corregidas; §4 tabla con columna ESTADO + §4.2-4.7 marcados (SA1/SA3/SA4/SA5 TO-BE, SA2/SA6/KG AS-IS parcial); §5 solo `query` AS-IS; §6 WS 0.5 Hz + ensamble sintético; §8 DDL anotado (matview TO-BE, `forecast_verification_log`/`weather_alerts` AS-IS no documentadas); §9 compose corregido.
- [x] **estacion_meteorologica.md** — banner **HISTÓRICO/DESFASADO** + tabla endpoints con columna ESTADO (5 AS-IS / 5 TO-BE) + §8 marcado (dump v3.1 vs v3.5 real, `extra=forbid` vs `ignore`).
- [x] **AUDITORIA_GAPS_DOCUMENTACION.md** — antes `??` sin trackear, ahora commiteada y pusheada. Fuente de verdad para gaps.
- [x] **Verificación** — `python -m py_compile app/*.py app/**/*.py` OK; `git status` limpio; `git push origin/main` OK.

### Código AS-IS que SÍ funciona (1,363 LOC reales)

- [x] FastAPI 3.5.0 (`app/main.py:27`) + 7 rutas + `WS /ws/telemetry/live` cada 2 s (`asyncio.sleep(2)` L107) + CORS + `static/index.html`.
- [x] `WeatherOrchestrator` + 4 tools FastMCP (`mcp_server.py` 4× `@mcp.tool`) + `physics_engine.py` (MetPy opcional con fallback Magnus-Tetens/Espy) + `schemas.py` (`extra=ignore`).
- [x] Semáforo 4 niveles + `assess_basin_hydrology_risk` con umbrales reales (`mcp_server.py:46-96`).
- [x] Gateway agnóstico OpenAI-compatible (`orchestrator.py:32-61`, `POST {base}/chat/completions`, fallback determinista sin key).
- [x] Dashboard `static/` (5 tarjetas, gauge CAPE 0-3500, ECharts 24h, abanico sintético p50/p90).
- [x] Firmware ESP32 (`firmware/esp32_sensor_node.py` 91L, MQTT QoS 1, batería/IRQ) + `simulator/sensor_simulator.py` 51L + `database/init.sql` 51L (3 tablas, hypertable).
- [x] `graphify-out/` generado + `build_graph.py` 56L (`--budget 1500`).
- [x] **Prompt caching + dedup LLM** (`ab24d0f`) — `SYSTEM_*_STATIC` cacheables con `cache_control: ephemeral` (Anthropic/OpenRouter 90% ahorro prefix; inocuo en OpenAI) + dedup local hash TTL 60s evita 2 calls idénticos en <60s → 100% ahorro en polling. Vars `LLM_ENABLE_PROMPT_CACHE/LLM_CACHE_TTL/LLM_PROMPT_CACHE_LOG` en `.env.example`.

---

## ⏳ Pendiente — Priorizado (TO-BE honesto)

### P0 — Bloquea deploy real (hacer con inteligencia media, <1 USD, 2-3h)

- [ ] **P0.1 Cablear persistencia o documentar demo en memoria** — `requirements` trae `asyncpg/psycopg2/redis/paho-mqtt` pero `app/` no los importa (auditoría §1.2). Opción A: cablear `sensor_telemetry` → TimescaleDB en `POST /telemetry/ingest` + `GET /history`; Opción B: documentar honesto "modo demo en memoria" y mover DDL/Redis/MQTT a `docs/TO-BE/`. Archivos: `app/main.py`, `app/mcp_server.py`, `database/init.sql`.
- [ ] **P0.2 `/health` + test smoke + logging** — hoy sin `GET /health`, sin `tests/`, sin CI, logging no estructurado; healthchecks solo en `timescaledb`/`redis`. Añadir `GET /health` (DB ping si existe), `tests/test_smoke.py` (1 test `GET /api/v1/dashboard/overview` 200), `ruff` o `pytest`. Archivos: `app/main.py`, `tests/`, `.github/workflows/`.
- [ ] **P0.3 Validar compose end-to-end** — con `.env` real, `docker compose up --build` y `curl localhost:8000/api/v1/dashboard/overview` + `curl localhost:8000/health` deben dar 200 dentro y fuera de Docker (LLM sin key → fallback, no 500).

### P1 — Funcionalidad regional / deuda docs (1-2h)

- [ ] **P1.1 Fórmulas Xalapa faltantes** — niebla `T-Td<=0.8 && LCL<=1450` y convección severa `CAPE>=1800, CIN>=-40, PWAT>=40, LI<=-3` solo en memoria §2.1, no en `physics_engine.py` (hoy `is_norte` usa umbrales absolutos `P>864 && T<18`). Decidir: implementar en `physics_engine.py:85` o dejar como spec documentada y marcar TO-BE en SDD.
- [ ] **P1.2 Archivar duplicación** — `estacion_meteorologica.md` ya marcado histórico; siguiente: mover a `docs/archivo/` o borrar dump duplicado y dejar solo §2.1 (fórmulas) + §3 (comunidades) como `docs/spec-regional.md`.
- [ ] **P1.3 Sincronizar DDL** — `telemetry_5min` (TO-BE en SDD) no está en `init.sql`; `forecast_verification_log`/`weather_alerts` están en SQL pero no se escriben. Decidir: añadir matview o borrar del SDD y cablear escrituras.

### P2 — ML avanzado (reservar inteligencia superior Grok 4.6, solo cuando haya datos)

- [ ] **P2.1 Super-ensamble LightGBM cuantílico** — hoy sintético pseudoaleatorio (`orchestrator.py:163-189`). Requiere datos históricos + features orográficos.
- [ ] **P2.2 Nowcasting pysteps + GOES-16** — flujo Lucas-Kanade, Banda 13 IR + GLM (0-120 min).
- [ ] **P2.3 Verificación CRPS/CSI + EMA closed-loop** — `forecast_verification_log` + recalibración BMA.
- [ ] **P2.4 Downscaling / S2S MJO/CAMS/ERA5** — solo cuando P0/P1 estén cerrados.

---

## 📋 Para el próximo agente — checklist de mano

- [ ] Leer `AUDITORIA_GAPS_DOCUMENTACION.md` §0-§1.4 + `CHECKLIST.md` (este archivo).
- [ ] Elegir siguiente `[ ]` de P0, implementar, `python -m py_compile`, `git diff --stat`, marcar `[x]` aquí, `git commit` + `git push`.
- [ ] No regenerar `graph.json`/`GRAPH_REPORT.md` como "avance" (son generados).
- [ ] No reintroducir claims falsos en README/SDD; respetar AS-IS vs TO-BE.

## 💰 Nota sobre uso de LLMs (Grok 4.6: 6.5 USD gastados)

- **P0/P1 → inteligencia media/económica** (suficiente, 1/3 costo, sin alucinar docs). Grok cobró 6.5 USD por ~1,363 LOC + docs inflados; P0/P1 reales son 2-3h mecánicas.
- **P2 → Grok 4.6 superior SÍ vale** (LightGBM, pysteps, CRPS/EMA, GOES) — razonamiento pesado justificado solo con datos históricos.

---

## 📜 Historial de commits

- `30f703e` (2026-08-14) — docs: corregir 4 MD post-auditoría AS-IS vs TO-BE + dotenv + compose
- `ab24d0f` (2026-08-14) — feat(llm): prompt caching + dedup (SYSTEM_*_STATIC + cache_control + TTL 60s)
- `3d8829b` — feat: gateway provider-agnostic (Grok)
- `7cf0bf9` — docs: SDD.md v1.1.0
- `11ba55e` — feat: initial commit (5,583 líneas incl. PDF + graph.json)
