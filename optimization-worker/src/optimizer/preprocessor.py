"""Preprocessing: validate input and optionally cluster large instances.

For > decomposition_threshold deliveries, geographic clustering (K-Means) splits
the problem into sub-problems solved independently then merged (ARCHITECTURE §4.1).
"""

from __future__ import annotations

import math

import numpy as np
from sklearn.cluster import KMeans

from optimizer.config import get_settings
from optimizer.models import Delivery, OptimizationError, VRPProblem

settings = get_settings()


def validate(problem: VRPProblem) -> None:
    if not problem.deliveries:
        raise OptimizationError("infeasible: no deliveries")
    if not problem.vehicles:
        raise OptimizationError("infeasible: no vehicles")
    if problem.respect_capacity:
        total_demand = sum(d.demand for d in problem.deliveries)
        total_capacity = sum(v.capacity for v in problem.vehicles)
        if total_demand > total_capacity:
            raise OptimizationError("infeasible: total demand exceeds fleet capacity")


def needs_decomposition(problem: VRPProblem) -> bool:
    return len(problem.deliveries) >= settings.decomposition_threshold


def cluster(problem: VRPProblem) -> list[VRPProblem]:
    """Split a large instance into geographic sub-problems (K-Means on lat/lon).

    Chooses k = ⌈n / threshold⌉ clusters, capped at the vehicle count (each cluster
    needs at least one vehicle). Vehicles are distributed to clusters in proportion
    to cluster size (every cluster gets ≥1). Each sub-problem keeps the parent's
    constraints + objective and is solved independently, then merged.
    """
    deliveries = problem.deliveries
    n = len(deliveries)
    num_vehicles = len(problem.vehicles)
    k = min(max(1, math.ceil(n / settings.decomposition_threshold)), num_vehicles)
    if k <= 1:
        return [problem]

    coords = np.array([[d.lat, d.lon] for d in deliveries])
    labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(coords)

    grouped: list[list[Delivery]] = [[] for _ in range(k)]
    for d, label in zip(deliveries, labels, strict=True):
        grouped[int(label)].append(d)

    # Distribute vehicles proportionally to cluster size, guaranteeing ≥1 each.
    sizes = [len(g) for g in grouped]
    counts = [1] * k
    for _ in range(num_vehicles - k):
        # give the next vehicle to the cluster with the most deliveries per vehicle.
        idx = max(range(k), key=lambda i: sizes[i] / counts[i])
        counts[idx] += 1

    subs: list[VRPProblem] = []
    v = 0
    for i in range(k):
        vehicles = problem.vehicles[v : v + counts[i]]
        v += counts[i]
        subs.append(
            VRPProblem(
                depot=problem.depot,
                deliveries=grouped[i],
                vehicles=vehicles,
                respect_time_windows=problem.respect_time_windows,
                respect_capacity=problem.respect_capacity,
                objective=problem.objective,
            )
        )
    return subs
