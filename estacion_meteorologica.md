---
título: Memoria técnica y dinámica regional — IvekBot Weather Station
doc_id: DOC-003-01
versión: 1.3.0
estado: HÍBRIDO
audiencia: ambos
idioma: es-ES
verificado_en:
  commit: 1513c19
  fecha: 2026-08-14
  método: lectura_código
  archivos_clave:
    - app/physics_engine.py
    - app/mcp_server.py
    - app/main.py
    - app/schemas.py
    - graphify-out/GRAPH_REPORT.md
reglas:
  - "Este archivo guarda ciencia de dominio. No es un tercer SDD."
  - "No numerar agentes. No pegar código vivo."
prohibido:
  - "Afirmar que las fórmulas de §2.1 están cableadas si no hay ruta:línea."
  - "Nombrar comunidades Graphify que el reporte deja anónimas."
---

# Memoria técnica: dinámica regional y metodología

- **Proyecto:** IvekBot Weather Station
- **Ubicación de referencia:** Xalapa, Veracruz, México ($19.54^\circ\text{N},\, 96.92^\circ\text{W}$, $1{,}420\,\text{msnm}$) — microclima de bosque de niebla y alta orografía
- **Contratos de software:** [SDD.md](SDD.md)
- **Cómo correr la demo:** [README.md](README.md)

Este documento **no implementa**. Conserva el marco científico de Xalapa y apunta al código cuando hay un umbral distinto.

---

## Estado de implementación (capa científica)

| Capacidad | Archivo real | Status | Evidencia |
|---|---|---|---|
| Rocío Magnus-Tetens / MetPy | `app/physics_engine.py` | AS-IS | `:13-28` |
| LCL Espy/Bolton / MetPy | `app/physics_engine.py` | AS-IS | `:31-47` |
| CAPE/CIN/PWAT/LI heurísticos | `app/physics_engine.py` | AS-IS | `:64-78` (no sounding) |
| Norte por umbrales absolutos | `app/physics_engine.py` | AS-IS | `:85` |
| Norte ΔP3h / ΔT3h / racha 50 | — | dominio / **TO-BE:** | §2.1; no en código |
| Convección CAPE≥1800, CIN≥−40, PWAT≥40, LI≤−3 | — | dominio / **TO-BE:** | §2.1; código usa otros cortes en riesgo |
| Niebla $T-T_d\le 0.8$ y LCL≤1450 msnm | — | dominio / **TO-BE:** | §2.1; no hay detector |
| Semáforo 4 niveles | `app/mcp_server.py` | AS-IS | `:46-96` |
| Cuencas Actopan / La Antigua / Sordo | `app/mcp_server.py` | texto | docstring `:44` y acciones `:67` |
| Nowcast pysteps / GOES / NWP / LightGBM | — | **TO-BE:** | marco §2, no runtime |

---

## 1. Alcance de esta memoria

Cinco capas de **intención metodológica**. Solo la capa 1 (física de superficie) y parte de la 4 (semáforo + texto) están en `app/` hoy.

1. Determinista / física de superficie.
2. Numérica / ML (NWP, downscaling) — **TO-BE:**
3. GraphRAG (grafo generado; no memoria de runtime).
4. Síntesis de riesgo y boletín (función + LLM opcional).
5. Dashboard (ver SDD §6; no repetir C4 aquí).

---

## 2. Métodos del estado del arte (marco de dominio, no runtime)

> Ejemplo ilustrativo de horizonte científico. **No usar como inventario de módulos instalados.**

```
+-----------------------+-----------------------------------+-------------------------------------------------+
| HORIZONTE             | FENÓMENO OBJETIVO                 | METODOLOGÍA (MARCO)                             |
+-----------------------+-----------------------------------+-------------------------------------------------+
| Nowcasting (0 - 6 h)  | Tormentas, granizo, ráfagas,      | Flujo óptico (Lucas-Kanade) / pysteps,           |
|                       | niebla local                      | GOES-16 Banda 13 IR (10.3 µm) + GLM, MetPy      |
+-----------------------+-----------------------------------+-------------------------------------------------+
| Corto / medio         | Nortes, ondas tropicales,         | Super-ensamble (ECMWF IFS/AIFS, GFS, ICON,      |
| (6 h - 14 días)       | lluvia acumulada                  | HRRR) + downscaling LightGBM                    |
+-----------------------+-----------------------------------+-------------------------------------------------+
| Sub-estacional / S2S  | Anomalías, canícula, frentes      | MJO (RMM1/RMM2), CAMS AOD, climatología ERA5    |
| (14 días - 3 meses)   | tardíos                           | 1991-2020                                       |
+-----------------------+-----------------------------------+-------------------------------------------------+
```

Ninguna fila de esa tabla está cableada como pipeline. El “ensamble 14d” AS-IS es `_generate_ensemble_14d` sintético (`app/agents/orchestrator.py:260`).

### 2.1 Dinámica meteorológica regional (Caso Xalapa / Barlovento Veracruzano)

**Bloque protegido.** No borrar ni “corregir” para igualarlo al `if` de `physics_engine.py`.

1. **Fenómeno del "Norte" (Surge Polar / Advección Baroclínica):**
   - Disparo de dominio: salto barométrico ($\Delta P_{3\text{h}} \ge +2.5\,\text{hPa}$), giro del viento a $330^\circ - 360^\circ$, ráfagas $\ge 50\,\text{km/h}$ y descenso térmico ($\Delta T_{3\text{h}} \le -4.0\,^\circ\text{C}$).
2. **Convección severa de verano (forzamiento orográfico + brisa marina):**
   - Disparo de dominio: $\text{CAPE} \ge 1{,}800\,\text{J/kg}$, $\text{CIN} \ge -40\,\text{J/kg}$, $\text{PWAT} \ge 40\,\text{mm}$, $\text{LI} \le -3.0$.
3. **Niebla orográfica (*bosque de niebla*):**
   - Disparo de dominio: depresión del punto de rocío $(T - T_d \le 0.8\,^\circ\text{C})$ y LCL $\le 1{,}450\,\text{msnm}$.

#### Recuadro: dominio vs código

| Fenómeno | Dominio (esta sección) | Código AS-IS | Quién manda dónde |
|---|---|---|---|
| Norte | ΔP3h ≥ +2.5 hPa, Dir 330–360°, racha ≥ 50, ΔT3h ≤ −4.0 °C | `P>864 ∧ T<18 ∧ Dir∈[300,360]∪[0,30]` → `app/physics_engine.py:85` | Código en runtime; dominio en spec |
| Convección | CAPE≥1800, CIN≥−40, PWAT≥40, LI≤−3 | CAPE heurístico `[0,4000]` `:69`; riesgo usa CAPE≥2000∧lluvia≥10 o CAPE>1200 (`mcp_server.py:60`, `:80`) | No unificar en silencio |
| Niebla | $T-T_d\le 0.8$, LCL≤1450 msnm | no hay detector; LCL se calcula en hPa (`:31`) | **TO-BE:** |
| Racha naranja | ≥ 50 km/h (Norte de dominio) | ≥ 55 km/h (`mcp_server.py:52`) | ambas citadas |
| Cuencas | Río Actopan, Río La Antigua, Río Sordo | solo texto de alerta (`mcp_server.py:44`, `:67`) | no hay modelo de cuenca |

---

## 3. Graphify (artefacto, no spec)

Graphify indexa el repo en `graphify-out/graph.json`. Consulta AS-IS: `query_graphify_knowledge` (`app/mcp_server.py:100`), presupuesto por argumento (default 1500).

El reporte [graphify-out/GRAPH_REPORT.md](graphify-out/GRAPH_REPORT.md) (2026-08-14) tiene 88 nodos, 167 edges y comunidades anónimas “Community 0…8”. **No inventar** nombres del tipo “Protocolos de Inundación de la Cuenca Actopan”. `THEME` aislado = constante de color en `static/js/dashboard.js:9`.

God nodes útiles como evidencia de símbolos reales: `WeatherOrchestrator`, `TelemetryData`, `compute_atmospheric_physics`, `ThermodynamicIndices`, `RiskAssessment`.

**TO-BE:** `find_path` / `explain`; etiquetado semántico de comunidades.

---

## 4. Símbolos de runtime (sin numerar agentes)

Una sola lista. El diseño de roles futuros está en SDD §4bis.

| Símbolo | Rol |
|---|---|
| `TelemetryData` | payload de superficie (`app/schemas.py:13`, `extra="ignore"`) |
| `compute_atmospheric_physics` | física |
| `assess_basin_hydrology_risk` | semáforo |
| `_generate_ensemble_14d` | 14 días sintéticos |
| `_synthesize_summary_with_llm` / `_synthesize_bulletin_with_llm` | texto; fallback si no hay key |
| `WeatherOrchestrator.execute_pipeline` | orquesta lo anterior |

Endpoints reales: README. No existen `/telemetry/history`, `/thermodynamics/sounding`, `/radar/frames`, `/alerts/publish`.

---

## 5. Wireframe de dashboard (ejemplo ilustrativo)

> Ejemplo ilustrativo. No usar como dato real. Temp 24.5 °C no es telemetría viva.

Intención de layout (6 paneles: telemetría, mapa radar, series, Skew-T, ensamble 14d, asistente). **AS-IS** en `static/`: tarjetas + ECharts + gauge + abanico sintético. Mapa Leaflet y Skew-T = **TO-BE:** (SDD §6).

---

## 6. Referencias de implementación (no dumps)

| Tema | Fuente |
|---|---|
| Schemas | `app/schemas.py` |
| API / WS | `app/main.py` |
| Firmware | `firmware/esp32_sensor_node.py` |
| DDL | `database/init.sql` |
| Compose | `docker-compose.yml` |
| Contratos de módulo y LLM | SDD §4 y §5 |

---

## Fórmulas protegidas (checklist T4)

- [x] Norte de dominio ΔP3h / viento / racha 50 / ΔT3h.
- [x] Convección CAPE≥1800 / CIN≥−40 / PWAT≥40 / LI≤−3.
- [x] Niebla $T-T_d\le 0.8$ y LCL≤1450 msnm.
- [x] Coordenadas 19.54°N, 96.92°W y 1420 msnm.
- [x] Cuencas Actopan, La Antigua, Sordo.
- [x] Semáforo de 4 niveles (runtime en `mcp_server.py`).
- [x] Magnus-Tetens y LCL Espy/Bolton citados como fallback de código, no como “MetPy garantizado”.
- [x] Norte AS-IS de código citado, no sustituye a §2.1.
- [x] Cero dumps de Python/HTML/SQL/YAML.
- [x] Cero tercera jerarquía de agentes.

## Checklist de aceptación (revisor LLM)

- [x] Front-matter HÍBRIDO, commit `1513c19`.
- [x] §2 y §2.1 conservados.
- [x] Recuadro dominio vs código.
- [x] Sin `extra="forbid"`, sin FastAPI 3.1.0, sin dumps.
- [ ] Revisor humano: marcar este ítem al aceptar.
