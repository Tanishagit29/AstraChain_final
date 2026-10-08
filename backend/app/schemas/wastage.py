from typing import Optional
from pydantic import BaseModel, ConfigDict


class WastageCreate(BaseModel):
    item_code: str
    product: str
    batch: str
    quantity: str
    reason: str
    loss_amount: str
    severity: Optional[str] = "MEDIUM"
    agent_intervention: Optional[str] = None


class WastageUpdate(BaseModel):
    quantity: Optional[str] = None
    reason: Optional[str] = None
    loss_amount: Optional[str] = None
    severity: Optional[str] = None
    agent_intervention: Optional[str] = None


class WastageItemOut(BaseModel):
    id: str
    product: str
    batch: str
    quantity: str
    reason: str
    lossAmount: str
    severity: str
    agentIntervention: str

    model_config = ConfigDict(from_attributes=True)


class DiscountRecommendationOut(BaseModel):
    product_name: str
    batch: str
    days_to_expiry: int
    current_price: str
    recommended_discount: str
    expected_sales_lift: str
