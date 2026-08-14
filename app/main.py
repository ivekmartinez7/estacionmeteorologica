import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.schemas import (
    DashboardOverview,
    TelemetryData,
    ThermodynamicIndices,
    RiskAssessment,
    ForecastReport,
    KnowledgeQueryRequest
)
from app.physics_engine import compute_atmospheric_physics
from app.mcp_server import query_graphify_knowledge
from app.agents.orchestrator import WeatherOrchestrator

app = FastAPI(
    title="IvekBot Weather Station Platform API",
    version="3.5.0",
    description="Plataforma Meteorológica Digital Multi-Agente con Graphify (GraphRAG), WebSockets y FastMCP"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado global en memoria para la estación
current_telemetry = TelemetryData(
    station_id="XAL-CENTRO-01",
    temperature_c=24.5,
    humidity_pct=84.0,
    pressure_hpa=861.2,
    rain_rate_mmh=1.2,
    rain_accum_24h_mm=14.5,
    wind_speed_kmh=15.0,
    wind_gust_kmh=26.0,
    wind_direction_deg=65.0,
    battery_v=4.18
)

history_buffer: List[Dict[str, Any]] = []
orchestrator = WeatherOrchestrator()


class ConnectionManager:
    """Gestiona conexiones activas de WebSockets para dashboards en tiempo real."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message, default=str))
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    # Inicializar buffer histórico de 24 horas simuladas
    now = datetime.utcnow()
    for i in range(24, 0, -1):
        t_stamp = now - timedelta(hours=i)
        t_val = round(21.0 + 4.5 * (1.0 - abs((t_stamp.hour - 14) / 12.0)) + random.uniform(-0.5, 0.5), 1)
        h_val = round(95.0 - (t_val - 18.0) * 3.5 + random.uniform(-2, 2), 1)
        p_val = round(862.0 - (t_val - 20.0) * 0.3 + random.uniform(-0.4, 0.4), 1)
        history_buffer.append({
            "time": t_stamp.strftime("%H:%M"),
            "temperature_c": t_val,
            "humidity_pct": h_val,
            "pressure_hpa": p_val,
            "rain_accum_mm": round(max(0.0, 14.5 - (i * 0.6)), 1),
            "wind_speed_kmh": round(8.0 + random.uniform(0, 12), 1)
        })

    # Iniciar background loop de emisión periódica en WebSocket
    asyncio.create_task(simulate_realtime_weather_stream())


async def simulate_realtime_weather_stream():
    """Generador en tiempo real de telemetría viva para clientes conectados."""
    global current_telemetry
    while True:
        await asyncio.sleep(2)  # Cada 2 segundos emite un pulso
        # Pequeña variación estocástica continua
        current_telemetry.temperature_c = round(current_telemetry.temperature_c + random.uniform(-0.15, 0.15), 1)
        current_telemetry.humidity_pct = round(max(40.0, min(100.0, current_telemetry.humidity_pct + random.uniform(-0.5, 0.5))), 1)
        current_telemetry.pressure_hpa = round(current_telemetry.pressure_hpa + random.uniform(-0.1, 0.1), 1)
        current_telemetry.wind_speed_kmh = round(max(0.0, current_telemetry.wind_speed_kmh + random.uniform(-0.8, 0.8)), 1)
        current_telemetry.wind_gust_kmh = round(max(current_telemetry.wind_speed_kmh, current_telemetry.wind_speed_kmh + random.uniform(4.0, 12.0)), 1)
        current_telemetry.timestamp = datetime.utcnow()

        thermo_dict = compute_atmospheric_physics(
            current_telemetry.temperature_c,
            current_telemetry.humidity_pct,
            current_telemetry.pressure_hpa,
            current_telemetry.wind_speed_kmh,
            current_telemetry.wind_direction_deg
        )

        packet = {
            "type": "telemetry_pulse",
            "telemetry": current_telemetry.model_dump(),
            "thermodynamics": thermo_dict
        }
        await manager.broadcast(packet)


@app.websocket("/ws/telemetry/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/v1/dashboard/overview", response_model=DashboardOverview)
async def get_dashboard_overview():
    report = await orchestrator.execute_pipeline(current_telemetry)
    return DashboardOverview(
        station_info={
            "station_id": current_telemetry.station_id,
            "name": "Estación Meteorológica Xalapa Centro",
            "coords": [19.5438, -96.9272],
            "elevation_msnm": 1420
        },
        current_telemetry=current_telemetry,
        thermodynamics=report.thermodynamics,
        risk=report.risk,
        executive_summary=report.executive_summary,
        recent_history=history_buffer[-24:],
        last_update=datetime.utcnow()
    )


@app.get("/api/v1/forecast/report", response_model=ForecastReport)
async def get_forecast_report():
    return await orchestrator.execute_pipeline(current_telemetry)


@app.post("/api/v1/telemetry/ingest")
async def ingest_telemetry(payload: Dict[str, Any]):
    global current_telemetry
    current_telemetry = TelemetryData(**payload)
    report = await orchestrator.execute_pipeline(current_telemetry)
    await manager.broadcast({
        "type": "telemetry_update",
        "telemetry": current_telemetry.model_dump(),
        "thermodynamics": report.thermodynamics.model_dump(),
        "risk": report.risk.model_dump()
    })
    return {"status": "SUCCESS", "forecast_id": report.forecast_id}


@app.post("/api/v1/knowledge/query")
async def query_knowledge(req: KnowledgeQueryRequest):
    res = query_graphify_knowledge(req.question, req.budget_tokens)
    return {"query": req.question, "result": res}


# Servir Frontend Dashboard
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def serve_dashboard():
        return FileResponse(str(static_dir / "index.html"))
