"""Deterministic K-Means for territory clustering (F15).

Pure Python (no numpy/sklearn in the API service) — city-scale delivery sets are
small, and squared-euclidean distance on lat/lon is an adequate proxy at that
scale. Initialisation is deterministic (evenly spaced over the sorted points) so
the same inputs always yield the same zones.
"""

from __future__ import annotations

Point = tuple[float, float]


def _closest(point: Point, centroids: list[Point]) -> int:
    px, py = point
    best_i, best_d = 0, float("inf")
    for i, (cx, cy) in enumerate(centroids):
        d = (px - cx) ** 2 + (py - cy) ** 2
        if d < best_d:
            best_i, best_d = i, d
    return best_i


def kmeans(points: list[Point], k: int, max_iter: int = 50) -> tuple[list[int], list[Point]]:
    """Return (assignment_per_point, centroids). k is clamped to [1, len(points)]."""
    n = len(points)
    if n == 0:
        return [], []
    k = max(1, min(k, n))

    order = sorted(range(n), key=lambda i: points[i])
    centroids: list[Point] = [points[order[(i * n) // k]] for i in range(k)]
    assignment = [0] * n

    for _ in range(max_iter):
        changed = False
        for i, p in enumerate(points):
            c = _closest(p, centroids)
            if c != assignment[i]:
                assignment[i] = c
                changed = True
        for c in range(k):
            members = [points[i] for i in range(n) if assignment[i] == c]
            if members:
                centroids[c] = (
                    sum(m[0] for m in members) / len(members),
                    sum(m[1] for m in members) / len(members),
                )
        if not changed:
            break

    return assignment, centroids
