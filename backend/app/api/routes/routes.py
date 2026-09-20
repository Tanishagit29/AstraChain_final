from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.routes import (
    RouteOut,
    RouteOptimizationRequest,
    MultiStopOptimizationRequest,
    MultiStopOptimizationResponse,
)
from app.services.route_service import RouteOptimizationService

router = APIRouter(prefix="/routes", tags=["Route Optimization"])

@router.get("", response_model=APIResponse[List[RouteOut]])
def get_routes(db: Session = Depends(get_db)):
    routes = RouteOptimizationService.get_all_routes(db)
    return APIResponse(
        success=True,
        message="Fleet routes retrieved successfully.",
        data=routes
    )

@router.get("/locations", response_model=APIResponse[List[str]])
def get_known_locations():
    """Returns the known delivery-network locations usable in multi-stop route planning."""
    return APIResponse(
        success=True,
        message="Known delivery network locations retrieved successfully.",
        data=RouteOptimizationService.get_known_locations()
    )

@router.post("/optimize", response_model=APIResponse[RouteOut])
def optimize_route(req: RouteOptimizationRequest, db: Session = Depends(get_db)):
    optimized = RouteOptimizationService.optimize_route(db, req)
    return APIResponse(
        success=True,
        message="Route optimized successfully via Agentic AI telemetry.",
        data=optimized
    )

@router.post("/optimize-multi-stop", response_model=APIResponse[MultiStopOptimizationResponse])
def optimize_multi_stop_route(req: MultiStopOptimizationRequest, db: Session = Depends(get_db)):
    """
    Multi-stop delivery route optimization (Vehicle Routing / TSP-style problem):
    solves the best visiting order across several delivery stops for one truck run
    using a Nearest-Neighbor construction heuristic refined with 2-Opt local search.
    """
    optimized = RouteOptimizationService.optimize_multi_stop(db, req)
    return APIResponse(
        success=True,
        message="Multi-stop route optimized successfully via Nearest Neighbor + 2-Opt heuristic.",
        data=optimized
    )

@router.get("/{route_code}", response_model=APIResponse[RouteOut])
def get_route_details(route_code: str, db: Session = Depends(get_db)):
    route = RouteOptimizationService.get_route_details(db, route_code)
    return APIResponse(
        success=True,
        message=f"Route details for '{route_code}' retrieved successfully.",
        data=route
    )
