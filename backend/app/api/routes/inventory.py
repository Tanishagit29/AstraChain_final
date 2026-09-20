from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.inventory import (
    InventoryItemOut, InventoryItemCreate, InventoryItemUpdate,
    InventoryPaginatedOut, ReorderRecommendationOut
)
from app.services.inventory_service import InventoryService
from app.api.deps import get_current_user
from app.models.all_models import User

router = APIRouter(prefix="/inventory", tags=["Inventory Intelligence"])


@router.get("", response_model=APIResponse[InventoryPaginatedOut])
def list_inventory(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    category: Optional[str] = None,
    warehouse: Optional[str] = None,
    risk: Optional[str] = None,
    db: Session = Depends(get_db)
):
    result = InventoryService.get_all_inventory(
        db, page=page, limit=limit, search=search, category=category, warehouse=warehouse, risk=risk
    )
    return APIResponse(
        success=True,
        message="Inventory items retrieved successfully.",
        data=result
    )


@router.get("/low-stock", response_model=APIResponse[List[InventoryItemOut]])
def get_low_stock(db: Session = Depends(get_db)):
    items = InventoryService.get_low_stock_items(db)
    return APIResponse(
        success=True,
        message="Low stock inventory items retrieved successfully.",
        data=items
    )


@router.get("/stockout-risk", response_model=APIResponse[List[InventoryItemOut]])
def get_stockout_risk(db: Session = Depends(get_db)):
    items = InventoryService.get_stockout_risk_items(db)
    return APIResponse(
        success=True,
        message="High stockout risk inventory items retrieved.",
        data=items
    )


@router.get("/overstock-risk", response_model=APIResponse[List[InventoryItemOut]])
def get_overstock_risk(db: Session = Depends(get_db)):
    items = InventoryService.get_overstock_risk_items(db)
    return APIResponse(
        success=True,
        message="Overstock risk inventory items retrieved.",
        data=items
    )


@router.get("/reorder-recommendations", response_model=APIResponse[List[ReorderRecommendationOut]])
def get_reorder_recommendations(db: Session = Depends(get_db)):
    recommendations = InventoryService.get_reorder_recommendations(db)
    return APIResponse(
        success=True,
        message="Reorder recommendations generated successfully.",
        data=recommendations
    )


@router.get("/{product_code}", response_model=APIResponse[InventoryItemOut])
def get_inventory_detail(product_code: str, db: Session = Depends(get_db)):
    item = InventoryService.get_inventory_item(db, product_code)
    return APIResponse(
        success=True,
        message=f"Inventory details for '{product_code}' retrieved.",
        data=item
    )


@router.post("", response_model=APIResponse[InventoryItemOut], status_code=status.HTTP_201_CREATED)
def create_inventory(
    item_in: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = InventoryService.create_inventory_item(db, item_in)
    return APIResponse(
        success=True,
        message=f"Inventory item '{item_in.product_code}' created successfully.",
        data=item
    )


@router.put("/{product_code}", response_model=APIResponse[InventoryItemOut])
def update_inventory(
    product_code: str,
    item_in: InventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = InventoryService.update_inventory_item(db, product_code, item_in)
    return APIResponse(
        success=True,
        message=f"Inventory item '{product_code}' updated successfully.",
        data=item
    )


@router.delete("/{product_code}", response_model=APIResponse[dict])
def delete_inventory(
    product_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = InventoryService.delete_inventory_item(db, product_code)
    return APIResponse(
        success=True,
        message=f"Inventory item '{product_code}' deleted successfully.",
        data=result
    )
