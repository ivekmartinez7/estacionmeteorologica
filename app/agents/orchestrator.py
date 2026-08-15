import os
import uuid
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
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
    """
    Orquestador Central Multi-Agente Provider-Agnostic.
    Permite al usuario conectar cualquier proveedor de LLM (OpenAI, OpenRouter,
    DeepSeek, Groq, Anthropic, Gemini, Ollama, vLLM o endpoints compatibles).
    """

    def __init__(self, station_id: str = "XAL-CENTRO-01", location: str = "Xalapa, Veracruz"):
        self.station_id = station_id
        self.location = location
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.orchestrator_model = os.getenv("ORCHESTRATOR_MODEL", "gpt-4o-mini")
        self.risk_agent_model = os.getenv("RISK_AGENT_MODEL", self.orchestrator_model)
        # Límites efectivos (antes hardcodeados; ahora leídos del .env)
        try:
            self.orchestrator_max_tokens = int(os.getenv("ORCHESTRATOR_MAX_TOKENS", "250"))
        except ValueError:
            self.orchestrator_max_tokens = 250
        try:
            self.risk_max_tokens = int(os.getenv("RISK_AGENT_MAX_TOKENS", "300"))
        except ValueError:
            self.risk_max_tokens = 300
        try:
            self.orchestrator_temperature = float(os.getenv("ORCHESTRATOR_TEMPERATURE", "0.3"))
        except ValueError:
            self.orchestrator_temperature = 0.3
        try:
            self.risk_temperature = float(os.getenv("RISK_AGENT_TEMPERATURE", "0.3"))
        except ValueError:
            self.risk_temperature = 0.3

    async def _call_llm(self, prompt: str, system_prompt: str, model_name: str, max_tokens: int = 1000, temperature: float = 0.3) -> Optional[str]:
        """Realiza una llamada genérica a cualquier API compatible con OpenAI / Token Plan."""
        if not self.llm_api_key or self.llm_api_key == "tu_api_key_aqui":
            return None

        url = f"{self.llm_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as err:
            print(f"[LLM Gateway] Error consultando API de LLM ({model_name}): {err}")

        return None

    async def execute_pipeline(self, telemetry: TelemetryData) -> ForecastReport:
        """
        Ejecuta el ciclo de vida completo del pronóstico:
        1. Subagente Ingesta & QC
        2. Subagente Físico / Termodinámico (Determinista MetPy)
        3. Subagente Riesgo Hidrológico & Cuencas
        4. Subagente Ensamble 14 Días
        5. Subagente Síntesis Cognitiva & Difusión (Vía LLM configurado o Motor Base)
        """
        # 1 & 2. Motor Físico Determinista (Coste $0)
        thermo_dict = compute_atmospheric_physics(
            temp_c=telemetry.temperature_c,
            rh_pct=telemetry.humidity_pct,
            pressure_hpa=telemetry.pressure_hpa,
            wind_speed_kmh=telemetry.wind_speed_kmh,
            wind_direction_deg=telemetry.wind_direction_deg
        )
        thermo = ThermodynamicIndices(**thermo_dict)

        # 3. Motor de Riesgo Hidrometeorológico
        risk_dict = assess_basin_hydrology_risk(
            rain_rate_mmh=telemetry.rain_rate_mmh,
            rain_accum_24h_mm=telemetry.rain_accum_24h_mm,
            cape_jkg=thermo.cape_jkg,
            wind_gust_kmh=telemetry.wind_gust_kmh,
            norte_surge=thermo.norte_surge_detected
        )
        risk = RiskAssessment(**risk_dict)

        # 4. Generación del Ensamble Sintético a 14 días
        ensemble = self._generate_ensemble_14d(telemetry.temperature_c, thermo)

        # 5. Síntesis Cognitiva vía LLM configurado por el usuario (o fallback automático)
        summary = await self._synthesize_summary_with_llm(telemetry, thermo, risk)
        bulletin = await self._synthesize_bulletin_with_llm(telemetry, thermo, risk)

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

    async def _synthesize_summary_with_llm(self, t: TelemetryData, th: ThermodynamicIndices, r: RiskAssessment) -> str:
        prompt = (
            f"Ubicación: {self.location}\n"
            f"Telemetría: Temp={t.temperature_c}°C, Humedad={t.humidity_pct}%, Presión={t.pressure_hpa}hPa, Viento={t.wind_speed_kmh}km/h (Racha: {t.wind_gust_kmh}km/h), Lluvia 24h={t.rain_accum_24h_mm}mm.\n"
            f"Termodinámica: CAPE={th.cape_jkg} J/kg, CIN={th.cin_jkg} J/kg, PWAT={th.pwat_mm}mm, Frente Frío Norte Activo: {th.norte_surge_detected}.\n"
            f"Nivel Alerta: {r.alert_level}, Riesgo Dominante: {r.dominant_hazard}.\n"
            "Genera un resumen meteorológico ejecutivo conciso (máximo 3 oraciones)."
        )
        sys_prompt = "Eres el meteorólogo jefe de la estación IvekBot. Genera resúmenes técnicos precisos basados estrictamente en los datos proporcionados."

        llm_response = await self._call_llm(prompt, sys_prompt, self.orchestrator_model, max_tokens=self.orchestrator_max_tokens, temperature=self.orchestrator_temperature)
        if llm_response:
            return llm_response

        # Fallback determinista si no hay API key configurada
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

    async def _synthesize_bulletin_with_llm(self, t: TelemetryData, th: ThermodynamicIndices, r: RiskAssessment) -> str:
        prompt = (
            f"Alerta: {r.alert_level}, Peligro: {r.dominant_hazard}, Temp: {t.temperature_c}°C, Lluvia 24h: {t.rain_accum_24h_mm}mm, Viento: {t.wind_speed_kmh}km/h.\n"
            f"Acciones recomendadas: {', '.join(r.recommended_actions)}.\n"
            "Redacta un aviso breve con emojis formateado para WhatsApp / Telegram / X para la población."
        )
        sys_prompt = "Genera avisos meteorológicos de Protección Civil claros, directos y con emojis informativos."

        llm_response = await self._call_llm(prompt, sys_prompt, self.risk_agent_model, max_tokens=self.risk_max_tokens, temperature=self.risk_temperature)
        if llm_response:
            return llm_response

        # Fallback determinista
        icon_map = {"VERDE": "🟢", "AMARILLO": "🟡", "NARANJA": "🟠", "ROJO": "🔴"}
        icon = icon_map.get(r.alert_level, "⚪")
        return (
            f"{icon} AVISO METEOROLÓGICO [{r.alert_level}] — Xalapa y Región\n"
            f"• Riesgo Dominante: {r.dominant_hazard.replace('_', ' ')}\n"
            f"• Temperatura: {t.temperature_c}°C | Humedad: {t.humidity_pct}% | Viento: {t.wind_speed_kmh} km/h\n"
            f"• Recomendación: {', '.join(r.recommended_actions[:2]) if r.recommended_actions else 'Mantener precauciones normales.'}"
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
