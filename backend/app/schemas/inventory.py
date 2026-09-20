from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class InventoryItemCreate(BaseModel):
    product_code: str
    name: str
    category: str
    current_stock: int
    forecast_demand: int
    days_remaining: int
    progress: Optional[int] = 50
    risk: Optional[str] = "HEALTHY"
    action: Optional[str] = "Optimal level"
    warehouse: Optional[str] = "Mumbai Central"
    unit_cost: str = "₹100"


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    current_stock: Optional[int] = None
    forecast_demand: Optional[int] = None
    days_remaining: Optional[int] = None
    progress: Optional[int] = None
    risk: Optional[str] = None
    action: Optional[str] = None
    warehouse: Optional[str] = None
    unit_cost: Optional[str] = None


class InventoryItemOut(BaseModel):
    id: str
    name: str
    category: str
    currentStock: int
    forecastDemand: int
    daysRemaining: int
    progress: int
    risk: str
    action: str
    warehouse: str
    unitCost: str

    # Calculated metrics
    safetyStock: Optional[int] = None
    reorderPoint: Optional[int] = None
    avgDailyDemand: Optional[float] = None
    stockoutProbability: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryPaginatedOut(BaseModel):
    items: List[InventoryItemOut]
    total: int
    page: int
    limit: int
    pages: int


class ReorderRecommendationOut(BaseModel):
    product_id: str
    product_name: str
    current_stock: int
    safety_stock: int
    reorder_point: int
    suggested_reorder_qty: int
    supplier: str
    urgency: str
