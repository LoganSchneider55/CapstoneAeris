# app/aqi.py
# Simple AQI conversion for PM2.5, PM10 (µg/m³), O3 (ppm 8-hr), CO (ppm 8-hr)
# Returns (aqi:int|None, category:str)

from typing import Optional, Tuple

# Each tuple: (C_low, C_high, I_low, I_high, category)
PM25 = [
    (0.0,   12.0,   0,   50,  "Good"),
    (12.1,  35.4,  51,  100,  "Moderate"),
    (35.5,  55.4, 101,  150,  "Unhealthy for Sensitive Groups"),
    (55.5, 150.4, 151,  200,  "Unhealthy"),
    (150.5,250.4, 201,  300,  "Very Unhealthy"),
    (250.5,500.4, 301,  500,  "Hazardous"),
]

PM10 = [
    (0,    54,    0,   50,  "Good"),
    (55,   154,  51,  100,  "Moderate"),
    (155,  254, 101,  150,  "Unhealthy for Sensitive Groups"),
    (255,  354, 151,  200,  "Unhealthy"),
    (355,  424, 201,  300,  "Very Unhealthy"),
    (425,  604, 301,  500,  "Hazardous"),
]

O3_8H = [
    (0.000, 0.054,   0,   50, "Good"),
    (0.055, 0.070,  51,  100, "Moderate"),
    (0.071, 0.085, 101,  150, "Unhealthy for Sensitive Groups"),
    (0.086, 0.105, 151,  200, "Unhealthy"),
    (0.106, 0.200, 201,  300, "Very Unhealthy"),
    # Above this typically uses 1-hr table; we cap at 300 here.
]

CO_8H = [
    (0.0,   4.4,   0,   50, "Good"),
    (4.5,   9.4,  51,  100, "Moderate"),
    (9.5,  12.4, 101,  150, "Unhealthy for Sensitive Groups"),
    (12.5, 15.4, 151,  200, "Unhealthy"),
    (15.5, 30.4, 201,  300, "Very Unhealthy"),
    (30.5, 50.4, 301,  500, "Hazardous"),
]

TABLES = {
    "pm25": PM25,
    "pm10": PM10,
    "o3":   O3_8H,  # value must be in ppm
    "co":   CO_8H,  # value must be in ppm
}

# Device payload label -> canonical pollutant key used for AQI/thresholds
# (We still store the ORIGINAL sensor_type in the DB; this is only for AQI lookup.)
SENSOR_ALIASES = {
    "pm25_ugm3": "pm25",
    "pm10_ugm3": "pm10",
    "co_ppm":    "co",
    "co":        "co",
}

def _interp(c_low: float, c_high: float, i_low: int, i_high: int, c: float) -> int:
    # Linear interpolation per EPA formula, rounded to nearest integer
    if c_high == c_low:
        return i_high
    aqi = (i_high - i_low) / (c_high - c_low) * (c - c_low) + i_low
    return int(round(aqi))

def canonical_pollutant(sensor_type: Optional[str]) -> Optional[str]:
    """
    Map an incoming sensor_type string (e.g., 'pm25_ugm3', 'co_ppm') to the
    canonical pollutant key this module knows AQI tables for ('pm25','pm10','co','o3').
    Returns None if unsupported.
    """
    if not sensor_type:
        return None
    st = SENSOR_ALIASES.get(sensor_type.strip().lower(), sensor_type.strip().lower())
    return st if st in TABLES else None

def compute_aqi(sensor_type: str, value: float) -> Tuple[Optional[int], str]:
    """
    Returns (aqi, category). If sensor_type unsupported or out of range, returns (None, "Unknown"/"Out of range").
    Accepts device labels (e.g., 'pm25_ugm3', 'pm10_ugm3', 'co_ppm') transparently.
    """
    key = canonical_pollutant(sensor_type)
    if not key:
        return None, "Unknown"

    table = TABLES[key]
    for c_low, c_high, i_low, i_high, cat in table:
        if c_low <= value <= c_high:
            return _interp(c_low, c_high, i_low, i_high, value), cat

    return None, "Out of range"
