from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict

class RouteOut(BaseModel):
    id: str
    truckId: str
    driver: str
    origin: str
    destination: str
    status: str
    eta: str
    temp: str
    fuelSaved: str
    risk: str

    model_config = ConfigDict(from_attributes=True)

class RouteOptimizationRequest(BaseModel):
    truck_id: str
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    destination: str
    avoid_traffic: bool = True


# ---------------------------------------------------------------------------
# Multi-Stop Route Optimization (Vehicle Routing / TSP-style)
# ---------------------------------------------------------------------------

class MultiStopOptimizationRequest(BaseModel):
    truck_id: str
    origin: str = "Mumbai Central Port"
    stops: List[str]
    return_to_origin: bool = False


class RouteLegOut(BaseModel):
    from_location: str
    to_location: str
    distance_km: float
    duration_minutes: int


class MultiStopOptimizationResponse(BaseModel):
    truck_id: str
    origin: str
    naive_sequence: List[str]
    optimized_sequence: List[str]
    legs: List[RouteLegOut]
    algorithm: str
    total_stops: int
    total_distance_km: float
    naive_distance_km: float
    distance_saved_km: float
    total_duration_minutes: int
    fuel_cost_inr: float
    naive_fuel_cost_inr: float
    fuel_saved_inr: float
    savings_pct: float


class KnownLocationsOut(BaseModel):
    locations: List[str]
