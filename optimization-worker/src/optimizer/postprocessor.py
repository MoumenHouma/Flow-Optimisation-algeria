"""Postprocessing: serialize solution for persistence + notify subscribers."""

from __future__ import annotations

from optimizer.models import VRPSolution


def solution_to_result(
    solution: VRPSolution,
    duration_ms: int,
    geometries: dict[str, dict] | None = None,
) -> dict:
    """Shape a VRPSolution into the JSONB stored on optimization_jobs.result.

    `geometries` maps vehicle_id -> GeoJSON LineString (OSRM /route); when absent
    the route's geometry is None and the client falls back to straight lines.
    """
    geometries = geometries or {}
    return {
        "strategy": solution.strategy,
        "is_suboptimal": solution.is_suboptimal,
        "total_distance_m": solution.total_distance_m,
        "total_time_s": solution.total_time_s,
        "total_fuel_l": solution.total_fuel_l,
        "total_co2_kg": solution.total_co2_kg,
        "objective_value": solution.objective_value,
        "duration_ms": duration_ms,
        "routes": [
            {
                "vehicle_id": r.vehicle_id,
                "total_distance_m": r.total_distance_m,
                "total_time_s": r.total_time_s,
                "fuel_l": r.fuel_l,
                "co2_kg": r.co2_kg,
                "geometry": geometries.get(r.vehicle_id),
                "stops": [
                    {"delivery_id": s.delivery_id, "sequence": s.sequence, "eta_s": s.eta_s}
                    for s in r.stops
                ],
            }
            for r in solution.routes
        ],
    }
