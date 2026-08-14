import json
import subprocess
from typing import Dict, Any
from fastmcp import FastMCP
from app.schemas import TelemetryData, ThermodynamicIndices, RiskAssessment
from app.physics_engine import compute_atmospheric_physics

mcp = FastMCP("IvekBot-Weather-Orchestrator")


@mcp.tool()
def ingest_and_validate_telemetry(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Asimila, valida y aplica control de calidad (QC) a los datos de la estación física.
    """
    telemetry = TelemetryData(**raw_payload)
    if telemetry.temperature_c > 45.0 or telemetry.humidity_pct > 100.0:
        telemetry.qc.is_valid = False
    return telemetry.model_dump()


@mcp.tool()
def calculate_thermodynamics(temp_c: float, rh_pct: float, pressure_hpa: float, wind_dir_deg: float = 0.0) -> Dict[str, Any]:
    """
    Ejecuta el cálculo determinista de termodinámica atmosférica (CAPE, CIN, LCL, PWAT, Norte).
    """
    return compute_atmospheric_physics(
        temp_c=temp_c,
        rh_pct=rh_pct,
        pressure_hpa=pressure_hpa,
        wind_direction_deg=wind_dir_deg
    )


@mcp.tool()
def assess_basin_hydrology_risk(
    rain_rate_mmh: float,
    rain_accum_24h_mm: float,
    cape_jkg: float,
    wind_gust_kmh: float,
    norte_surge: bool
) -> Dict[str, Any]:
    """
    Evalúa el riesgo hidrometeorológico en la cuenca Xalapa / Actopan / La Antigua.
    """
    alert_level = "VERDE"
    dominant_hazard = "NINGUNO"
    prob_overflow = 0.05
    urban_flood = False
    actions = ["Monitoreo estándar de variables meteorológicas"]

    if norte_surge or wind_gust_kmh >= 55.0:
        alert_level = "NARANJA"
        dominant_hazard = "VIENTO_NORTE"
        actions = [
            "Asegurar techumbres y objetos ligeros por fuertes rachas de viento",
            "Manejar con precaución en autopista Xalapa-Perote"
        ]

    if rain_rate_mmh >= 25.0 or rain_accum_24h_mm >= 50.0 or (cape_jkg >= 2000.0 and rain_rate_mmh >= 10.0):
        alert_level = "NARANJA" if alert_level != "ROJO" else "ROJO"
        dominant_hazard = "LLUVIA_TORRENCIAL"
        prob_overflow = 0.55
        urban_flood = True
        actions.extend([
            "Alerta por encharcamientos severos en avenidas principales de Xalapa",
            "Vigilancia activa en niveles del Río Sordo y Río Actopan"
        ])

    if rain_accum_24h_mm >= 100.0:
        alert_level = "ROJO"
        dominant_hazard = "INUNDACION"
        prob_overflow = 0.85
        urban_flood = True
        actions = [
            "EVACUACIÓN PREVENTIVA en zonas de alto riesgo de deslave",
            "Cierre preventivo de vados y pasos a desnivel",
            "Activación de albergues temporales de Protección Civil"
        ]
    elif alert_level == "VERDE" and (rain_rate_mmh > 0.0 or cape_jkg > 1200.0):
        alert_level = "AMARILLO"
        dominant_hazard = "LLUVIA_TORRENCIAL"
        prob_overflow = 0.20
        actions = [
            "Precaución por pavimento mojado",
            "Posible reducción de visibilidad por bancos de niebla"
        ]

    risk = RiskAssessment(
        alert_level=alert_level,
        dominant_hazard=dominant_hazard,
        basin_overflow_prob=prob_overflow,
        urban_flood_risk=urban_flood,
        recommended_actions=actions
    )
    return risk.model_dump()


@mcp.tool()
def query_graphify_knowledge(question: str, budget_tokens: int = 1500) -> str:
    """
    Realiza una consulta semántica GraphRAG al Grafo de Conocimiento del proyecto mediante Graphify.
    """
    try:
        cmd = ["graphify", "query", question, "--budget", str(budget_tokens)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
        return f"Grafo consultado: no se encontraron rutas directas para '{question}'."
    except Exception as e:
        return f"Error ejecutando Graphify: {str(e)}"
