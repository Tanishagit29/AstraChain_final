from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.forecast import (
    ForecastItem,
    GenerateForecastRequest,
    ProductForecastResponse,
    FestivalCalendarItem,
    FestivalImpactItem,
    FestivalForecastResponse,
    FestivalItemDemandResponse,
)
from app.services.forecast_service import ForecastService
from app.services.festival_service import FestivalForecastService

router = APIRouter(prefix="/forecast", tags=["Demand Forecasting"])


@router.get("", response_model=APIResponse[List[ForecastItem]])
def get_forecasts(db: Session = Depends(get_db)):
    forecasts = ForecastService.get_forecasts(db)
    return APIResponse(
        success=True,
        message="Demand forecast records retrieved successfully.",
        data=forecasts
    )


@router.get("/festivals/calendar", response_model=APIResponse[List[FestivalCalendarItem]])
def get_festival_calendar(year: Optional[int] = Query(None, description="Calendar year; defaults to current + next year")):
    """Returns the Indian festival reference calendar with per-category demand multipliers."""
    years = [year] if year else None
    calendar = FestivalForecastService.get_calendar(years)
    return APIResponse(
        success=True,
        message="Festival demand calendar retrieved successfully.",
        data=calendar
    )


@router.get("/festivals/upcoming", response_model=APIResponse[List[FestivalImpactItem]])
def get_upcoming_festivals(
    category: str = Query("General", description="Product category to compute the expected uplift for"),
    within_days: int = Query(60, ge=1, le=365),
):
    """Returns upcoming festivals within a window, with the expected demand uplift for a category."""
    upcoming = FestivalForecastService.get_upcoming_festivals(category, within_days)
    return APIResponse(
        success=True,
        message=f"Upcoming festivals within {within_days} days retrieved successfully.",
        data=upcoming
    )


@router.get("/festivals/item-demand", response_model=APIResponse[FestivalItemDemandResponse])
def get_festival_item_demand(
    festival_name: Optional[str] = Query(None, description="Festival name (e.g. Diwali, Holi, Eid al-Fitr, Christmas, Ganesh Chaturthi)"),
    horizon_days: int = Query(60, ge=7, le=365),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Festival-wise item demand prediction: predicts which items will be sold more
    in the respective festival, ranking items by surge multiplier, sales volume,
    stock risk, and extra inventory buffer needed.
    """
    result = FestivalForecastService.get_festival_item_demand(
        db,
        festival_name=festival_name,
        horizon_days=horizon_days,
        limit=limit
    )
    return APIResponse(
        success=True,
        message=f"Item-level demand predictions generated for festival '{result.festival_name}'.",
        data=result
    )



@router.get("/{product_id}/festival-forecast", response_model=APIResponse[FestivalForecastResponse])
def get_product_festival_forecast(
    product_id: str,
    horizon_days: int = Query(60, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """
    Festival-wise demand forecast: layers Indian-festival demand-uplift
    multipliers (category-aware) on top of the base XGBoost/baseline forecast
    so upcoming spikes (Diwali, Eid, Christmas, etc.) are visible ahead of time.
    """
    result = FestivalForecastService.get_product_festival_forecast(db, product_id, horizon_days=horizon_days)
    return APIResponse(
        success=True,
        message=f"Festival-adjusted demand forecast generated for product '{product_id}'.",
        data=result
    )


@router.get("/{product_id}", response_model=APIResponse[ProductForecastResponse])
def get_product_forecast(
    product_id: str,
    horizon_days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    result = ForecastService.get_product_forecast(db, product_id, horizon_days=horizon_days)
    return APIResponse(
        success=True,
        message=f"Demand forecast generated for product '{product_id}'.",
        data=result
    )


@router.post("/generate", response_model=APIResponse[List[ForecastItem]])
def generate_forecast(req: GenerateForecastRequest, db: Session = Depends(get_db)):
    forecasts = ForecastService.generate_forecast(db, req)
    return APIResponse(
        success=True,
        message=f"Generated and persisted new forecast for horizon {req.horizon_days} days.",
        data=forecasts
    )
