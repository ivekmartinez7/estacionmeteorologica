import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.schemas import (
    ForecastReport,
    TelemetryData,
    ThermodynamicIndices,
    RiskAssessment,
    EnsembleForecastDay
)
from app.physics_engine import compute_atmospheric_physics
from app.mcp_server import assess_basin_hydrology_risk


class WeatherOrchestrator:
    """Orquestador Central Multi-Agente para la estación meteorológica."""

    def __init__(self, station_id: str = "XAL-CENTRO-01", location: str = "Xalapa, Veracruz"):
        self.station_id = station_id
        self.location = location

    async def execute_pipeline(self, telemetry: TelemetryData) -> ForecastReport:
        """
        Ejecuta el ciclo de vida completo del pronóstico:
        1. Subagente Ingesta & QC
        2. Subagente Físico / Termodinámico
        3. Subagente Riesgo Hidrológico & Cuencas
        4. Subagente Ensamble 14 Días
        5. Subagente Síntesis Cognitiva & Difusión
        """
        # 1. Motor Físico Determinista
        thermo_dict = compute_atmospheric_physics(
            temp_c=telemetry.temperature_c,
            rh_pct=telemetry.humidity_pct,
            pressure_hpa=telemetry.pressure_hpa,
            wind_speed_kmh=telemetry.wind_speed_kmh,
            wind_direction_deg=telemetry.wind_direction_deg
        )
        thermo = ThermodynamicIndices(**thermo_dict)

        # 2. Motor de Riesgo Hidrometeorológico
        risk_dict = assess_basin_hydrology_risk(
            rain_rate_mmh=telemetry.rain_rate_mmh,
            rain_accum_24h_mm=telemetry.rain_accum_24h_mm,
            cape_jkg=thermo.cape_jkg,
            wind_gust_kmh=telemetry.wind_gust_kmh,
            norte_surge=thermo.norte_surge_detected
        )
        risk = RiskAssessment(**risk_dict)

        # 3. Generación del Ensamble Sintético a 14 días (ECMWF/GFS/AIFS)
        ensemble = self._generate_ensemble_14d(telemetry.temperature_c, thermo)

        # 4. Síntesis Cognitiva
        summary = self._generate_executive_summary(telemetry, thermo, risk)
        bulletin = self._generate_public_bulletin(risk, telemetry, thermo)

        return ForecastReport(
            forecast_id=f"FCST-{uuid.uuid4().hex[:8].upper()}",
            generated_at=datetime.utcnow(),
            target_location=self.location,
            telemetry=telemetry,
            thermodynamics=thermo,
            risk=risk,
            executive_summary=summary,
            public_bulletin=bulletin,
            ensemble_14d=ensemble
        )

    def _generate_ensemble_14d(self, current_temp: float, thermo: ThermodynamicIndices) -> List[EnsembleForecastDay]:
        days = []
        now = datetime.utcnow()
        for i in range(14):
            day_date = (now + timedelta(days=i)).strftime("%Y-%m-%d")
            t_min = round(current_temp - 8.0 + (i * 0.2), 1)
            t_max = round(current_temp + 3.5 - (i * 0.1), 1)
            p10 = max(0.0, round(2.0 + (i % 3) * 1.5, 1))
            p50 = round(p10 + 6.5 + ((i * 2) % 12), 1)
            p90 = round(p50 + 15.0 + ((i * 3) % 20), 1)

            cond = "Soleado / Parcialmente Nublado"
            if p50 > 15.0:
                cond = "Tormentas Dispersas"
            elif p50 > 5.0:
                cond = "Chubascos Aislados"

            days.append(EnsembleForecastDay(
                date=day_date,
                temp_min_c=t_min,
                temp_max_c=t_max,
                rain_p10_mm=p10,
                rain_p50_mm=p50,
                rain_p90_mm=p90,
                dominant_condition=cond
            ))
        return days

    def _generate_executive_summary(self, t: TelemetryData, th: ThermodynamicIndices, r: RiskAssessment) -> str:
        if th.norte_surge_detected:
            return (
                f"Frente Frío ('Norte') activo en {self.location}. Viento sostenido de {t.wind_speed_kmh} km/h "
                f"con rachas de {t.wind_gust_kmh} km/h. Descenso térmico y lluvias ligeras a moderadas."
            )
        if th.cape_jkg > 1500:
            return (
                f"Alta inestabilidad atmosférica (CAPE: {th.cape_jkg} J/kg, Agua Precipitable: {th.pwat_mm} mm). "
                f"Forzamiento orográfico favorece tormentas convectivas vespertinas con potencial de descargas eléctricas."
            )
        return (
            f"Condiciones meteorológicas estables en {self.location}. Temperatura actual: {t.temperature_c} °C, "
            f"Humedad: {t.humidity_pct}%, Presión: {t.pressure_hpa} hPa. No se prevén eventos severos inmediatos."
        )

    def _generate_public_bulletin(self, r: RiskAssessment, t: TelemetryData, th: ThermodynamicIndices) -> str:
        icon_map = {"VERDE": "🟢", "AMARILLO": "🟡", "NARANJA": "🟠", "ROJO": "🔴"}
        icon = icon_map.get(r.alert_level, "⚪")
        return (
            f"{icon} AVISO METEOROLÓGICO [{r.alert_level}] — Xalapa y Región\n"
            f"• Riesgo Dominante: {r.dominant_hazard.replace('_', ' ')}\n"
            f"• Temperatura: {t.temperature_c}°C | Humedad: {t.humidity_pct}% | Viento: {t.wind_speed_kmh} km/h\n"
            f"• Recomendación: {', '.join(r.recommended_actions[:2]) if r.recommended_actions else 'Mantener precauciones normales.'}"
        )
