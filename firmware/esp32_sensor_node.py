"""
Firmware MicroPython para Nodo IoT ESP32 (Estación Meteorológica)
Conecta sensores de superficie (BME280 / Anemómetro / Pluviómetro)
y publica telemetría periódica vía MQTT con QoS 1 y reconexión automática.
"""

import time
import ujson
import network
from umqtt.simple import MQTTClient
from machine import Pin, I2C, ADC

# Configuración WiFi y MQTT
WIFI_SSID = "Meteorologia_Net"
WIFI_PASS = "ClaveSegura2026"
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
STATION_ID = "XAL-CENTRO-01"
TOPIC_TELEMETRY = "telemetry/xalapa"

# Pines de Sensores (Ejemplo de asignación de hardware)
PIN_RAIN_GAUGE = 4     # Pluviómetro de balancín (Interrupción por pulso)
PIN_ANEMOMETER = 5     # Sensor Hall para velocidad de viento
PIN_BATTERY = 34       # Divisor resistivo para lectura ADC de batería LiPo

rain_pulse_count = 0

def rain_interrupt_handler(pin):
    global rain_pulse_count
    rain_pulse_count += 1

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando a WiFi:", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASS)
        retry_count = 0
        while not wlan.isconnected() and retry_count < 20:
            time.sleep(0.5)
            retry_count += 1
    return wlan.isconnected()

def read_battery_voltage(adc_pin_num=PIN_BATTERY):
    adc = ADC(Pin(adc_pin_num))
    adc.atten(ADC.ATTN_11DB)
    raw = adc.read()
    # Calibración para divisor 1:2
    voltage = (raw / 4095.0) * 3.3 * 2.0
    return round(voltage, 2)

def main():
    global rain_pulse_count
    rain_pin = Pin(PIN_RAIN_GAUGE, Pin.IN, Pin.PULL_UP)
    rain_pin.irq(trigger=Pin.IRQ_FALLING, handler=rain_interrupt_handler)

    while True:
        if not connect_wifi():
            time.sleep(5)
            continue

        try:
            client = MQTTClient(STATION_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
            client.connect()
            print("Conectado a Broker MQTT:", MQTT_BROKER)

            while True:
                # Cada 5 segundos realiza lectura y publicación
                # En hardware real: bme.values para temperatura, humedad, presión
                calc_rain_mm = rain_pulse_count * 0.2794  # 0.2794 mm por pulso estándar
                rain_pulse_count = 0  # Reset ventana

                payload = {
                    "station_id": STATION_ID,
                    "temperature_c": 24.5,
                    "humidity_pct": 82.0,
                    "pressure_hpa": 861.5,
                    "rain_rate_mmh": round(calc_rain_mm * 12.0, 2),
                    "wind_speed_kmh": 14.2,
                    "battery_v": read_battery_voltage()
                }

                client.publish(TOPIC_TELEMETRY, ujson.dumps(payload), qos=1)
                time.sleep(5)

        except Exception as e:
            print("Error en transmisión MQTT:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
