"""
Multi-Stop Route Optimization Engine
=====================================
Implements a genuine route-sequencing optimizer for multi-drop delivery
runs, rather than a single fixed origin->destination lookup.

Algorithm: this is a classic (multi-stop) Traveling Salesman Problem.
We solve it with:
  1. Nearest-Neighbor construction heuristic — builds a fast initial tour
     by always hopping to the closest unvisited stop.
  2. 2-Opt local search improvement — repeatedly reverses tour segments
     whenever doing so shortens total travel distance, escaping the
     greedy local-minima that Nearest-Neighbor alone gets stuck in.

Both are O(n^2) / O(n^2) per pass respectively, which is more than fast
enough for realistic delivery-run sizes (a handful to a few dozen stops).
"""

import math
from typing import Dict, List, Tuple

Coordinate = Tuple[float, float]


def haversine_km(coord1: Coordinate, coord2: Coordinate) -> float:
    """Great-circle distance between two (lat, lng) points, in kilometers."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371.0  # Earth radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def tour_distance(tour: List[str], coords: Dict[str, Coordinate]) -> float:
    """Total distance for a full node sequence (including origin at index 0)."""
    total = 0.0
    for i in range(len(tour) - 1):
        total += haversine_km(coords[tour[i]], coords[tour[i + 1]])
    return total


# Backwards-compatible alias
_tour_distance = tour_distance


def nearest_neighbor_tour(origin: str, stops: List[str], coords: Dict[str, Coordinate]) -> List[str]:
    """
    Construct an initial tour by greedily visiting the nearest unvisited stop
    at each step, starting from `origin`.
    """
    remaining = list(stops)
    tour = [origin]
    current = origin

    while remaining:
        nearest = min(remaining, key=lambda s: haversine_km(coords[current], coords[s]))
        tour.append(nearest)
        remaining.remove(nearest)
        current = nearest

    return tour


def two_opt(tour: List[str], coords: Dict[str, Coordinate], max_iterations: int = 200) -> List[str]:
    """
    Improve a tour using the 2-opt local search heuristic: for every pair of
    edges in the tour, check whether reversing the segment between them
    produces a shorter total route. The origin (index 0) is held fixed as
    the fleet start point.
    """
    best = list(tour)
    best_distance = tour_distance(best, coords)
    improved = True
    iterations = 0

    n = len(best)
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1

        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                candidate_distance = tour_distance(candidate, coords)
                if candidate_distance < best_distance - 1e-9:
                    best = candidate
                    best_distance = candidate_distance
                    improved = True

    return best


def optimize_tour(origin: str, stops: List[str], coords: Dict[str, Coordinate]) -> List[str]:
    """Full pipeline: Nearest-Neighbor construction followed by 2-Opt refinement."""
    if not stops:
        return [origin]
    if len(stops) == 1:
        return [origin, stops[0]]

    initial = nearest_neighbor_tour(origin, stops, coords)
    refined = two_opt(initial, coords)
    return refined


def route_legs(tour: List[str], coords: Dict[str, Coordinate], avg_speed_kmph: float = 45.0) -> List[Dict]:
    """Break a tour down into per-leg distance & duration segments."""
    legs = []
    for i in range(len(tour) - 1):
        dist = haversine_km(coords[tour[i]], coords[tour[i + 1]])
        duration_min = int(round((dist / avg_speed_kmph) * 60))
        legs.append({
            "from_location": tour[i],
            "to_location": tour[i + 1],
            "distance_km": round(dist, 2),
            "duration_minutes": max(1, duration_min),
        })
    return legs
