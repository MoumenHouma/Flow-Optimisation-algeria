"""Cost components for multi-objective optimization (F14).

The objective combines distance, travel time, fuel and CO2. Fuel and CO2 depend
on the vehicle type (Algerian mixed-fleet reality, PRD §4.2) — a motorbike is far
cheaper to run than a truck, so an eco-weighted objective prefers greener vehicles.

Components are normalized to comparable natural units (km / min / L / kg) before
weighting, so a preset weight means what it says instead of being dominated by the
raw magnitude of metres. Fuel/CO2 also carry a small idle-burn term proportional to
travel time, so they are not a pure multiple of distance (congestion costs fuel).
The normalized sum is scaled back to integers for OR-Tools; with the default
distance-only weights the arc cost equals metres, so single-objective behaviour is
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

# Idle/low-speed burn: ~0.6 L/h → ml per second. Makes fuel depend on time, not
# only distance, so congested (slow) arcs cost more fuel than fast ones.
_IDLE_FUEL_ML_PER_S = 0.17
_CO2_G_PER_L = 2300.0  # petrol tailpipe, grams CO2 per litre
_COST_SCALE = 1000  # integer resolution for the normalized objective


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


def fuel_ml(distance_m: float, duration_s: float, factors: EmissionFactors) -> float:
    """Fuel over an arc (ml): travel burn (L/100km) + idle burn (per second)."""
    return distance_m * factors.fuel_l_per_100km / 100.0 + duration_s * _IDLE_FUEL_ML_PER_S


def co2_g(distance_m: float, duration_s: float, factors: EmissionFactors) -> float:
    """CO2 over an arc (g): tailpipe from travel + from idle fuel."""
    idle_l = duration_s * _IDLE_FUEL_ML_PER_S / 1000.0
    return distance_m / 1000.0 * factors.co2_g_per_km + idle_l * _CO2_G_PER_L


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
    """Weighted integer arc cost over normalized components (km/min/L/kg)."""
    normalized = (
        weights.distance * (distance_m / 1000.0)
        + weights.time * (duration_s / 60.0)
        + weights.fuel * (fuel_ml(distance_m, duration_s, factors) / 1000.0)
        + weights.co2 * (co2_g(distance_m, duration_s, factors) / 1000.0)
    )
    return int(round(normalized * _COST_SCALE))
