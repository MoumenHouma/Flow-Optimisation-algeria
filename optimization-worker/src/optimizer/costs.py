"""Cost components for multi-objective optimization (F14).

The objective combines distance, travel time, fuel and CO2. Fuel and CO2 depend
on the vehicle type via static consumption/emission factors (Algerian mixed-fleet
reality, PRD §4.2) — a motorbike is far cheaper to run than a truck, so an
eco-weighted objective naturally prefers greener vehicles for a given stop.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmissionFactors:
    fuel_l_per_100km: float
    co2_g_per_km: float


# Representative averages by vehicle type.
_FACTORS: dict[str, EmissionFactors] = {
    "motorcycle": EmissionFactors(3.0, 90.0),
    "car": EmissionFactors(7.0, 165.0),
    "van": EmissionFactors(9.0, 230.0),
    "truck": EmissionFactors(22.0, 700.0),
}
_DEFAULT = _FACTORS["car"]


def factors_for(vehicle_type: str) -> EmissionFactors:
    return _FACTORS.get(vehicle_type, _DEFAULT)


def fuel_ml(distance_m: float, factors: EmissionFactors) -> float:
    """Fuel used over an arc, in millilitres (L/100km → ml per metre)."""
    return distance_m * factors.fuel_l_per_100km / 100.0


def co2_g(distance_m: float, factors: EmissionFactors) -> float:
    return distance_m / 1000.0 * factors.co2_g_per_km


@dataclass(frozen=True)
class ObjectiveWeights:
    distance: float = 1.0
    time: float = 0.0
    fuel: float = 0.0
    co2: float = 0.0


def arc_cost(
    distance_m: float,
    duration_s: float,
    factors: EmissionFactors,
    weights: ObjectiveWeights,
) -> int:
    """Weighted, integer arc cost. distance-only (default weights) == meters."""
    total = (
        weights.distance * distance_m
        + weights.time * duration_s
        + weights.fuel * fuel_ml(distance_m, factors)
        + weights.co2 * co2_g(distance_m, factors)
    )
    return int(round(total))
