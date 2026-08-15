-- Habilitar extensión TimescaleDB (si está disponible en el motor PostgreSQL)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. Tabla de telemetría física de alta frecuencia
CREATE TABLE IF NOT EXISTS sensor_telemetry (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    station_id VARCHAR(32) NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    humidity_pct DOUBLE PRECISION NOT NULL,
    pressure_hpa DOUBLE PRECISION NOT NULL,
    rain_rate_mmh DOUBLE PRECISION DEFAULT 0.0,
    rain_accum_24h_mm DOUBLE PRECISION DEFAULT 0.0,
    wind_speed_kmh DOUBLE PRECISION DEFAULT 0.0,
    wind_gust_kmh DOUBLE PRECISION DEFAULT 0.0,
    wind_direction_deg DOUBLE PRECISION DEFAULT 0.0,
    battery_v DOUBLE PRECISION DEFAULT 4.2,
    qc_valid BOOLEAN DEFAULT TRUE
);

-- Convertir en Hypertable para optimización de series de tiempo
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('sensor_telemetry', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
    END IF;
END $$;

-- 2. Tabla de auditoría y verificación continua (Closed-loop feedback)
CREATE TABLE IF NOT EXISTS forecast_verification_log (
    id BIGSERIAL PRIMARY KEY,
    forecast_id VARCHAR(64) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    valid_for TIMESTAMPTZ NOT NULL,
    predicted_temp DOUBLE PRECISION,
    observed_temp DOUBLE PRECISION,
    predicted_rain_mm DOUBLE PRECISION,
    observed_rain_mm DOUBLE PRECISION,
    error_mae DOUBLE PRECISION,
    crps_score DOUBLE PRECISION,
    model_weights_json JSONB
);

-- 3. Tabla de alertas y avisos emitidos
CREATE TABLE IF NOT EXISTS weather_alerts (
    id BIGSERIAL PRIMARY KEY,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    alert_level VARCHAR(16) NOT NULL,
    hazard_type VARCHAR(32) NOT NULL,
    message_text TEXT NOT NULL,
    channels_sent VARCHAR(64)[]
);

-- 4. Vista continua 5 min — TO-BE (documentada en SDD §8 pero aún no activa)
-- Descomentar cuando app/ consuma TimescaleDB. Hoy la app corre en memoria (ver SDD, README).
-- CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_5min
-- WITH (timescaledb.continuous) AS
-- SELECT time_bucket('5 minutes', time) AS bucket, station_id,
--        AVG(temperature_c) AS avg_temp, MAX(temperature_c) AS max_temp,
--        MIN(temperature_c) AS min_temp, AVG(humidity_pct) AS avg_humidity,
--        AVG(pressure_hpa) AS avg_pressure,
--        SUM(rain_rate_mmh * (5.0/60.0)) AS accum_rain_mm, MAX(wind_speed_kmh) AS max_wind_gust
-- FROM sensor_telemetry WHERE qc_valid = TRUE GROUP BY bucket, station_id;
