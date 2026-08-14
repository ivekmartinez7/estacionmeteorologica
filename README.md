# ⚡ IvekBot Weather Station — Estación Meteorológica Digital Multi-Agente

Sistema integral de meteorología digital autónoma con arquitectura híbrida (Física determinista + AI-NWP + FastMCP + Graphify GraphRAG + Dashboard reactivo en tiempo real con WebSockets).

---

## 🚀 Inicio Rápido (Local)

### 1. Requisitos Previos
- Python 3.10+ o Docker

### 2. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecutar el Servidor FastAPI & Dashboard
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Abre tu navegador en: **`http://localhost:8000`**

### 4. (Opcional) Ejecutar con Docker Compose
```bash
docker compose up -d --build
```

---

## 📊 Componentes del Sistema

- **`app/`**:
  - `main.py`: Servidor FastAPI con WebSockets (`/ws/telemetry/live`) y REST APIs.
  - `schemas.py`: Contratos de datos tipados en Pydantic v2.
  - `physics_engine.py`: Motor físico determinista (MetPy / Ecuaciones de Magnus-Tetens, CAPE, CIN, LCL, PWAT, Norte).
  - `mcp_server.py`: Servidor FastMCP con herramientas registradas para agentes LLM.
  - `agents/orchestrator.py`: Pipeline multi-agente y ensamble a 14 días.
- **`static/`**:
  - `index.html`: Dashboard moderno interactivo.
  - `css/style.css`: Estilos visuales dark-mode.
  - `js/dashboard.js`: Conexión WebSocket y renderizado de gráficas Apache ECharts.
- **`firmware/`**:
  - `esp32_sensor_node.py`: Firmware MicroPython para microcontrolador ESP32 con MQTT QoS 1.
- **`simulator/`**:
  - `sensor_simulator.py`: Generador de telemetría simulada para pruebas en vivo.
- **`database/`**:
  - `init.sql`: Script DDL para TimescaleDB / PostgreSQL con hypertables.
- **`graphify-out/`**:
  - Base de Conocimiento GraphRAG para LLMs con detección de comunidades y reducción de costo de tokens.

---

## 🧠 Integración Graphify (GraphRAG para LLMs)

Para consultar el Grafo de Conocimiento sin gastar tokens excesivos:
```bash
graphify query "¿Qué condiciones disparan la alerta por Norte en Xalapa?" --budget 1200
```
O directamente desde la interfaz del Dashboard o vía endpoint:
```bash
POST /api/v1/knowledge/query
{"question": "¿Cómo calcula el sistema el índice CAPE?", "budget_tokens": 1500}
```
