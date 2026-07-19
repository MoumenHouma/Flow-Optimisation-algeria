"""Postprocessing: serialize solution for persistence + notify subscribers."""

from __future__ import annotations

from optimizer.models import VRPSolution


def solution_to_result(solution: VRPSolution, duration_ms: int) -> dict:
    """Shape a VRPSolution into the JSONB stored on optimization_jobs.result."""
    return {
        "strategy": solution.strategy,
        "is_suboptimal": solution.is_suboptimal,
        "total_distance_m": solution.total_distance_m,
        "total_time_s": solution.total_time_s,
        "objective_value": solution.objective_value,
        "duration_ms": duration_ms,
        "routes": [
            {
                "vehicle_id": r.vehicle_id,
                "total_distance_m": r.total_distance_m,
                "total_time_s": r.total_time_s,
                "stops": [
                    {"delivery_id": s.delivery_id, "sequence": s.sequence, "eta_s": s.eta_s}
                    for s in r.stops
                ],
            }
            for r in solution.routes
        ],
    }
