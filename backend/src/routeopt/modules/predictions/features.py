"""Cohort feature extraction for the service-time model (F13).

The same cohort key is computed at training time (from a delivery + its history)
and at prediction time (from a delivery being optimized), so features must come
from fields available in both places: location, the scheduled time window, and
the order's own attributes (priority, weight, locale).
"""

from datetime import time

# A delivery is "servable" in these bands based on its time window; the exact
# minute doesn't generalize, the part of day does.
_MIN_SERVICE_S = 30
_MAX_SERVICE_S = 7200  # 2h — anything longer is noise, not on-site service
DEFAULT_SERVICE_S = 300


def geo_cell(lat: float | None, lon: float | None) -> str:
    """~1 km grid cell — coarse enough to pool neighbours, fine enough for quartier."""
    if lat is None or lon is None:
        return "na"
    return f"{round(lat, 2)},{round(lon, 2)}"


def hour_bucket(window_start: time | None) -> str:
    if window_start is None:
        return "any"
    if window_start.hour < 12:
        return "am"
    if window_start.hour < 17:
        return "pm"
    return "eve"


def weight_bucket(weight: float) -> str:
    if weight <= 0:
        return "none"
    if weight <= 5:
        return "light"
    if weight <= 20:
        return "med"
    return "heavy"


def cohort_key(
    lat: float | None,
    lon: float | None,
    window_start: time | None,
    priority: int,
    weight: float,
    address_locale: str,
) -> str:
    return "|".join(
        [
            geo_cell(lat, lon),
            hour_bucket(window_start),
            str(priority),
            weight_bucket(weight),
            address_locale or "fr",
        ]
    )


def is_valid_duration(seconds: float) -> bool:
    return _MIN_SERVICE_S <= seconds <= _MAX_SERVICE_S
