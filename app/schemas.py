from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SensorQualityControl(BaseModel):
    """Banderas de control de calidad para datos de sensores físicos."""
    is_valid: bool = True
    temp_zscore: float = Field(default=0.0, description="Z-score en ventana de 15 min")
    pressure_jump_flag: bool = Field(default=False, description="Salto barométrico > 2.0 hPa en < 5 min")


class TelemetryData(BaseModel):
    """Telemetría física de superficie enviada por la estación ESP32."""
    model_config = ConfigDict(extra="ignore")

    station_id: str = Field(default="XAL-CENTRO-01", description="ID único de la estación")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    temperature_c: float = Field(..., ge=-40.0, le=60.0, description="Temperatura en Celsius")
    humidity_pct: float = Field(..., ge=0.0, le=100.0, description="Humedad relativa en %")
    pressure_hpa: float = Field(..., ge=700.0, le=1100.0, description="Presión atmosférica en hPa")
    rain_rate_mmh: float = Field(default=0.0, ge=0.0, description="Tasa instantánea de lluvia (mm/h)")
    rain_accum_24h_mm: float = Field(default=0.0, ge=0.0, description="Lluvia acumulada 24h (mm)")
    wind_speed_kmh: float = Field(default=0.0, ge=0.0, description="Velocidad media del viento")
    wind_gust_kmh: float = Field(default=0.0, ge=0.0, description="Racha máxima de viento")
    wind_direction_deg: float = Field(default=0.0, ge=0.0, le=360.0, description="Dirección del viento en grados")
    battery_v: float = Field(default=4.15, ge=3.0, le=4.5, description="Voltaje de batería LiPo")
    qc: SensorQualityControl = Field(default_factory=SensorQualityControl)


class ThermodynamicIndices(BaseModel):
    """Índices de inestabilidad y física atmosférica calculados por MetPy."""
    dewpoint_c: float = Field(..., description="Punto de rocío en °C")
    cape_jkg: float = Field(..., description="Convective Available Potential Energy en J/kg")
    cin_jkg: float = Field(..., description="Convective Inhibition en J/kg")
    lifted_index: float = Field(..., description="Índice de Levantamiento (LI)")
    pwat_mm: float = Field(..., description="Agua Precipitable Total en mm")
    lcl_hpa: float = Field(..., description="Nivel de Condensación por Elevación en hPa")
    lfc_hpa: Optional[float] = Field(None, description="Nivel de Convección Libre en hPa")
    thermal_anomaly_c: float = Field(..., description="Diferencial térmico vs ERA5 30y")
    norte_surge_detected: bool = Field(default=False, description="Evento de Frente Frío / Norte activo")


class RiskAssessment(BaseModel):
    """Evaluación de riesgo hidrometeorológico."""
    alert_level: Literal["VERDE", "AMARILLO", "NARANJA", "ROJO"] = "VERDE"
    dominant_hazard: Literal["NINGUNO", "LLUVIA_TORRENCIAL", "VIENTO_NORTE", "NIEBLA_CERO_VIS", "INUNDACION"] = "NINGUNO"
    basin_overflow_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    urban_flood_risk: bool = False
    recommended_actions: List[str] = Field(default_factory=list)


class EnsembleForecastDay(BaseModel):
    """Pronóstico probabilístico diario del ensamble."""
    date: str
    temp_min_c: float
    temp_max_c: float
    rain_p10_mm: float
    rain_p50_mm: float
    rain_p90_mm: float
    dominant_condition: str


class ForecastReport(BaseModel):
    """Reporte integral consolidado por el Orquestador Multi-Agente."""
    forecast_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    target_location: str = "Xalapa, Veracruz"
    telemetry: TelemetryData
    thermodynamics: ThermodynamicIndices
    risk: RiskAssessment
    executive_summary: str
    public_bulletin: str
    ensemble_14d: Optional[List[EnsembleForecastDay]] = None


class DashboardOverview(BaseModel):
    """Payload consolidado para el Dashboard en tiempo real."""
    station_info: Dict[str, Any]
    current_telemetry: TelemetryData
    thermodynamics: ThermodynamicIndices
    risk: RiskAssessment
    executive_summary: str
    recent_history: List[Dict[str, Any]] = Field(default_factory=list)
    last_update: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeQueryRequest(BaseModel):
    """Petición de consulta GraphRAG a Graphify."""
    question: str
    budget_tokens: int = 1500
    dfs_trace: bool = False
