from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict


class ForecastItem(BaseModel):
    day: str
    historical: Optional[int] = None
    forecast: int
    confidenceUpper: int
    confidenceLower: int

    model_config = ConfigDict(from_attributes=True)


class GenerateForecastRequest(BaseModel):
    product_id: Optional[str] = None
    horizon_days: int = 7  # 7, 30, or 90 days
    category: Optional[str] = None


class ForecastAccuracyMetrics(BaseModel):
    mae: float
    rmse: float
    mape: float
    accuracy_pct: float


class ProductForecastResponse(BaseModel):
    product_id: str
    product_name: str
    category: str
    horizon_days: int
    trend: str  # "UPWARD", "STABLE", "DOWNWARD"
    growth_rate_pct: float
    total_forecast_demand: int
    daily_forecasts: List[ForecastItem]
    accuracy_metrics: Optional[ForecastAccuracyMetrics] = None


# ---------------------------------------------------------------------------
# Festival-Wise Demand Forecasting
# ---------------------------------------------------------------------------

class FestivalCalendarItem(BaseModel):
    festival: str
    date: str
    category_multipliers: Dict[str, float]
    default_multiplier: float
    window_before_days: int
    window_after_days: int


class FestivalImpactItem(BaseModel):
    festival: str
    date: str
    days_away: int
    category: str
    expected_multiplier: float
    expected_uplift_pct: float


class FestivalForecastResponse(BaseModel):
    product_id: str
    product_name: str
    category: str
    horizon_days: int
    baseline_total_demand: int
    festival_adjusted_total_demand: int
    extra_units_from_festivals: int
    upcoming_festivals: List[FestivalImpactItem]
    daily_forecasts: List[ForecastItem]
    festival_adjusted_forecasts: List[ForecastItem]


class FestivalItemDemand(BaseModel):
    product_id: str
    product_name: str
    category: str
    baseline_daily_demand: float
    festival_multiplier: float
    baseline_period_sales: int
    festival_period_sales: int
    extra_units_needed: int
    uplift_pct: float
    current_stock: Optional[int] = None
    stock_status: str
    surge_level: str  # "HIGH", "MODERATE", "STABLE"


class FestivalItemDemandResponse(BaseModel):
    festival_name: str
    festival_date: str
    days_away: int
    window_days: int
    top_category: str
    total_surge_units: int
    items: List[FestivalItemDemand]

