from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class SupplierCreate(BaseModel):
    supplier_code: str
    name: str
    category: str
    reliability_score: Optional[str] = "90.0%"
    on_time_delivery: Optional[str] = "90.0%"
    lead_time_avg: Optional[str] = "1.5 days"
    risk_level: Optional[str] = "LOW"
    status: Optional[str] = "VERIFIED"


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    reliability_score: Optional[str] = None
    on_time_delivery: Optional[str] = None
    lead_time_avg: Optional[str] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None


class SupplierOut(BaseModel):
    id: str
    name: str
    category: str
    reliabilityScore: str
    onTimeDelivery: str
    leadTimeAvg: str
    riskLevel: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class SupplierRiskOut(BaseModel):
    supplier_id: str
    supplier_name: str
    risk_level: str
    impact_area: str
    mitigation_suggestion: str
