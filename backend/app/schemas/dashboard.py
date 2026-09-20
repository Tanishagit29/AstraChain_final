from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class KPIMetricItem(BaseModel):
    value: str
    delta: Optional[str] = None
    status: str
    timeframe: Optional[str] = None
    subtitle: Optional[str] = None

class KPIMetrics(BaseModel):
    totalSales: KPIMetricItem
    inventoryHealth: KPIMetricItem
    stockoutRisks: KPIMetricItem
    wastageRate: KPIMetricItem

class HealthProgress(BaseModel):
    inventoryEfficiency: str = "82%"
    supplierReliability: str = "91%"
    routeOptimization: str = "87%"
    wastagePrevention: str = "96%"

class DashboardSummaryOut(BaseModel):
    kpiMetrics: Dict[str, Any]
    demandForecastData: List[Dict[str, Any]]
    aiRecommendations: List[Dict[str, Any]]
    recentActivityLogs: List[Dict[str, Any]]
    healthIndicators: Dict[str, Any]
