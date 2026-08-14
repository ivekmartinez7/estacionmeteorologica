import math
from typing import Dict, Any

try:
    import numpy as np
    import metpy.calc as mpcalc
    from metpy.units import units
    METPY_AVAILABLE = True
except ImportError:
    METPY_AVAILABLE = False


def calculate_dewpoint(temp_c: float, rh_pct: float) -> float:
    """Calcula el punto de rocío usando la ecuación de Magnus-Tetens."""
    if METPY_AVAILABLE:
        try:
            t = temp_c * units.degC
            rh = (rh_pct / 100.0) * units.dimensionless
            dp = mpcalc.dewpoint_from_relative_humidity(t, rh)
            return round(float(dp.to(units.degC).magnitude), 2)
        except Exception:
            pass
    # Magnus-Tetens fallback
    a = 17.27
    b = 237.7
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(max(1.0, rh_pct) / 100.0)
    dp = (b * alpha) / (a - alpha)
    return round(dp, 2)


def calculate_lcl(temp_c: float, dewpoint_c: float, pressure_hpa: float) -> float:
    """Calcula el Nivel de Condensación por Elevación (LCL en hPa)."""
    if METPY_AVAILABLE:
        try:
            t = temp_c * units.degC
            dp = dewpoint_c * units.degC
            p = pressure_hpa * units.hPa
            lcl_p, _ = mpcalc.lcl(p, t, dp)
            return round(float(lcl_p.to(units.hPa).magnitude), 1)
        except Exception:
            pass
    # Fórmula aproximada de Espy / Bolton para LCL
    # LCL_h = 125 * (T - Td) metros de elevación sobre superficie
    # Convertido a presión barométrica estándar:
    h_lcl = 125.0 * max(0.0, (temp_c - dewpoint_c))
    p_lcl = pressure_hpa * math.pow(1.0 - (0.0065 * h_lcl / (temp_c + 273.15)), 5.255)
    return round(p_lcl, 1)


def compute_atmospheric_physics(
    temp_c: float,
    rh_pct: float,
    pressure_hpa: float,
    wind_speed_kmh: float = 0.0,
    wind_direction_deg: float = 0.0,
    climatology_era5_temp: float = 22.4
) -> Dict[str, Any]:
    """
    Calcula el perfil termodinámico y determinista completo sin intervención de LLMs.
    """
    dewpoint = calculate_dewpoint(temp_c, rh_pct)
    lcl_hpa = calculate_lcl(temp_c, dewpoint, pressure_hpa)

    # Estimación de inestabilidad convectiva (CAPE / CIN)
    delta_t = temp_c - dewpoint
    # A mayor temperatura y humedad, mayor flotabilidad térmica potencial
    if temp_c > 22.0 and rh_pct > 70.0:
        base_cape = (temp_c - 18.0) * (rh_pct - 50.0) * 1.65
        cape = round(max(0.0, min(4000.0, base_cape)), 1)
        cin = round(-1.0 * max(10.0, (delta_t * 8.5)), 1)
        lifted_index = round(-1.0 * (cape / 400.0), 2)
    else:
        cape = round(max(0.0, (temp_c - 16.0) * 15.0), 1)
        cin = round(-1.0 * max(30.0, (delta_t * 12.0)), 1)
        lifted_index = round(max(-1.0, 6.0 - (cape / 250.0)), 2)

    # Agua Precipitable Total estimada (PWAT mm)
    pwat = round(max(10.0, min(65.0, (dewpoint * 1.6) + 10.5)), 1)

    # Nivel de Convección Libre (LFC)
    lfc_hpa = round(lcl_hpa - 55.0, 1) if cape > 500.0 else None

    # Detección de "Norte" (Frente Frío) en Xalapa:
    # Alta presión barométrica relativa, temperatura fría y viento del N/NW (315° - 360°)
    is_norte = (pressure_hpa > 864.0 and temp_c < 18.0 and (300.0 <= wind_direction_deg <= 360.0 or wind_direction_deg <= 30.0))

    thermal_anomaly = round(temp_c - climatology_era5_temp, 2)

    return {
        "dewpoint_c": dewpoint,
        "cape_jkg": cape,
        "cin_jkg": cin,
        "lifted_index": lifted_index,
        "pwat_mm": pwat,
        "lcl_hpa": lcl_hpa,
        "lfc_hpa": lfc_hpa,
        "thermal_anomaly_c": thermal_anomaly,
        "norte_surge_detected": is_norte
    }
