import os
import time
import hashlib
import uuid
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Prompts cacheables (estáticos, largos, prefix-cache friendly) ──────────────
# Para prompt caching (Anthropic/OpenRouter/OpenAI) el prefijo DEBE ser idéntico
# entre llamadas. Todo lo estático va aquí (cache hit 90% ahorro); lo dinámico
# va AL FINAL del user prompt (cache miss solo en el sufijo).
SYSTEM_SUMMARY_STATIC = (
    "Eres el meteorólogo jefe de la estación IvekBot Weather Station "
    "(XAL-CENTRO-01, Xalapa, Veracruz — 19.5438°N, -96.9272°W, 1420 msnm, "
    "bosque de niebla, alta orografía).\n"
    "MISIÓN: generar un resumen ejecutivo meteorológico CONCISO (máximo 3 oraciones, "
    "técnico, sin alucinaciones, en español neutro). "
    "Usa SOLO los datos proporcionados; no inventes valores ni eventos.\n"
    "REGLAS: 1) Si Norte activo → menciona rachas/descenso térmico. "
    "2) Si CAPE>1500 o PWAT>40 → menciona inestabilidad/convectividad. "
    "3) Si todo estable → indica estabilidad y valores actuales. "
    "4) No uses emojis aquí (solo en boletín). 5) Sé breve: ahorra tokens."
)

SYSTEM_BULLETIN_STATIC = (
    "Eres el redactor de Protección Civil de IvekBot Weather Station "
    "(Xalapa y región Actopan-La Antigua-Sordo).\n"
    "MISIÓN: redactar un aviso ciudadano BREVE con emojis, listo para "
    "WhatsApp/Telegram/X, en español neutro, sin tecnicismos innecesarios.\n"
    "FORMATO OBLIGATORIO:\n"
    "🟢/🟡/🟠/🔴 AVISO [NIVEL] — Xalapa y Región\n"
    "• Riesgo Dominante: <tipo>\n"
    "• Datos: Temp/Hum/Viento/Lluvia\n"
    "• Recomendación: 1-2 acciones concretas\n"
    "REGLAS: usa SOLO datos dados; no exageres; si VERDE, tono tranquilo."
)
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
        # ── Prompt cache + dedup (ahorro economía) ──────────────────────────
        # LLM_CACHE_TTL=0 desactiva cache local; LLM_CACHE_TTL=60 (default) evita
        # llamar 2× al LLM con telemetría idéntica en <60 s (ej. polling del dashboard).
        try:
            self._cache_ttl = int(os.getenv("LLM_CACHE_TTL", "60"))
        except ValueError:
            self._cache_ttl = 60
        self._cache: Dict[str, tuple[float, str]] = {}  # key -> (expires_at, value)
        self._enable_prompt_cache = os.getenv("LLM_ENABLE_PROMPT_CACHE", "1") not in ("0", "false", "False")
        self._prompt_cache_log = os.getenv("LLM_PROMPT_CACHE_LOG", "0") in ("1", "true", "True")

    async def _call_llm(self, prompt: str, system_prompt: str, model_name: str, max_tokens: int = 1000, temperature: float = 0.3) -> Optional[str]:
        """Llamada OpenAI-compatible con prompt caching (prefix-cache) + dedup local.

        - Prompt caching: system estático al INICIO (cache hit 90% en Anthropic/OpenRouter),
          datos dinámicos al FINAL del user prompt (solo sufijo no cacheable).
          Se envía `cache_control` en el system cuando el proveedor lo soporta; si no,
          es inocuo (el server lo ignora).
        - Dedup local: si la misma telemetría ya se consultó hace <TTL, no se llama.
        """
        if not self.llm_api_key or self.llm_api_key == "tu_api_key_aqui":
            return None

        # ── Dedup local por hash (ahorra 100% del call) ──────────────────
        dedup_key = ""
        if self._cache_ttl > 0:
            dedup_key = hashlib.sha256(f"{model_name}|{system_prompt[:80]}|{prompt}".encode()).hexdigest()[:16]
            hit = self._cache.get(dedup_key)
            if hit and hit[0] > time.time():
                if self._prompt_cache_log:
                    print(f"[LLM cache HIT local] {model_name} key={dedup_key}")
                return hit[1]
            # limpiar expirados cada ~20 calls
            if len(self._cache) > 64:
                now = time.time()
                self._cache = {k: v for k, v in self._cache.items() if v[0] > now}

        url = f"{self.llm_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json"
        }
        # ── Mensajes con cache_control en el system (Anthropic/OpenRouter) ─
        # El system es 100% estático (SYSTEM_*_STATIC) → cacheable.
        # El user lleva solo el sufijo dinámico (telemetría) → no rompe el prefijo.
        if self._enable_prompt_cache:
            messages = [
                {"role": "system", "content": [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    # Guardar en dedup local
                    if dedup_key:
                        self._cache[dedup_key] = (time.time() + self._cache_ttl, text)
                    return text
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
        # Sufijo dinámico (lo único que rompe el cache) — corto y al FINAL
        dynamic = (
            f"DATOS VIVOS — Xalapa Centro ({self.location})\n"
            f"Temp={t.temperature_c}°C Hum={t.humidity_pct}% Pres={t.pressure_hpa}hPa "
            f"Viento={t.wind_speed_kmh}km/h Racha={t.wind_gust_kmh}km/h Lluvia24h={t.rain_accum_24h_mm}mm\n"
            f"CAPE={th.cape_jkg} CIN={th.cin_jkg} PWAT={th.pwat_mm} Norte={th.norte_surge_detected}\n"
            f"Alerta={r.alert_level} Peligro={r.dominant_hazard}\n"
            "Tarea: resumen ejecutivo 3 oraciones."
        )
        llm_response = await self._call_llm(dynamic, SYSTEM_SUMMARY_STATIC, self.orchestrator_model, max_tokens=self.orchestrator_max_tokens, temperature=self.orchestrator_temperature)
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
        dynamic = (
            f"Alerta={r.alert_level} Peligro={r.dominant_hazard} Temp={t.temperature_c}°C Lluvia24h={t.rain_accum_24h_mm}mm Viento={t.wind_speed_kmh}km/h\n"
            f"Acciones: {', '.join(r.recommended_actions)}\n"
            "Tarea: aviso breve con emojis WhatsApp/Telegram/X."
        )
        llm_response = await self._call_llm(dynamic, SYSTEM_BULLETIN_STATIC, self.risk_agent_model, max_tokens=self.risk_max_tokens, temperature=self.risk_temperature)
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
