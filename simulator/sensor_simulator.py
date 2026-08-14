"""
Simulador de Estación Meteorológica en Python
Envía paquetes HTTP / MQTT a la API de FastAPI para pruebas locales y demostraciones en vivo.
"""

import time
import random
import requests

API_URL = "http://localhost:8000/api/v1/telemetry/ingest"

def run_simulation():
    print("Iniciando simulador de estación meteorológica ->", API_URL)
    temp = 24.0
    pressure = 861.0
    humidity = 82.0
    accum_rain = 12.0

    while True:
        try:
            # Simular fluctuaciones naturales
            temp = round(temp + random.uniform(-0.3, 0.3), 1)
            humidity = round(max(30.0, min(100.0, humidity + random.uniform(-0.8, 0.8))), 1)
            pressure = round(pressure + random.uniform(-0.15, 0.15), 1)
            wind = round(max(0.0, 12.0 + random.uniform(-4, 8)), 1)
            gust = round(wind + random.uniform(3, 10), 1)
            rain_rate = round(max(0.0, random.choice([0.0, 0.0, 0.0, 1.5, 4.2])), 1)
            accum_rain = round(accum_rain + (rain_rate * (3.0 / 3600.0)), 2)

            payload = {
                "station_id": "XAL-CENTRO-01",
                "temperature_c": temp,
                "humidity_pct": humidity,
                "pressure_hpa": pressure,
                "rain_rate_mmh": rain_rate,
                "rain_accum_24h_mm": accum_rain,
                "wind_speed_kmh": wind,
                "wind_gust_kmh": gust,
                "wind_direction_deg": random.randint(45, 90),
                "battery_v": 4.16
            }

            resp = requests.post(API_URL, json=payload, timeout=5)
            print(f"[{time.strftime('%H:%M:%S')}] Enviado: T={temp}°C, H={humidity}%, P={pressure}hPa -> Status: {resp.status_code}")
        except Exception as e:
            print("Error conectando con la API:", e)

        time.sleep(3)

if __name__ == "__main__":
    run_simulation()
