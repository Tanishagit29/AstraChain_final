from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.wastage import WastageItemOut, WastageCreate, WastageUpdate, DiscountRecommendationOut
from app.services.wastage_service import WastageService
from app.api.deps import get_current_user
from app.models.all_models import User

router = APIRouter(prefix="/wastage", tags=["Wastage Prevention"])


@router.get("", response_model=APIResponse[List[WastageItemOut]])
def get_all_wastage(db: Session = Depends(get_db)):
    items = WastageService.get_all_wastage(db)
    return APIResponse(
        success=True,
        message="Wastage items retrieved successfully.",
        data=items
    )


@router.get("/near-expiry", response_model=APIResponse[List[WastageItemOut]])
def get_near_expiry_items(db: Session = Depends(get_db)):
    items = WastageService.get_near_expiry_items(db)
    return APIResponse(
        success=True,
        message="Near-expiry wastage items retrieved.",
        data=items
    )


@router.get("/discount-recommendations", response_model=APIResponse[List[DiscountRecommendationOut]])
def get_discount_recommendations(db: Session = Depends(get_db)):
    recs = WastageService.get_discount_recommendations(db)
    return APIResponse(
        success=True,
        message="Dynamic discount recommendations generated.",
        data=recs
    )


@router.get("/expected-waste", response_model=APIResponse[dict])
def get_expected_waste(db: Session = Depends(get_db)):
    data = WastageService.get_expected_waste(db)
    return APIResponse(
        success=True,
        message="Expected wastage loss financial summary retrieved.",
        data=data
    )


@router.post("", response_model=APIResponse[WastageItemOut], status_code=status.HTTP_201_CREATED)
def create_wastage(
    w_in: WastageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = WastageService.create_wastage_item(db, w_in)
    return APIResponse(
        success=True,
        message=f"Wastage record '{w_in.item_code}' created successfully.",
        data=item
    )


@router.put("/{item_code}", response_model=APIResponse[WastageItemOut])
def update_wastage(
    item_code: str,
    w_in: WastageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = WastageService.update_wastage_item(db, item_code, w_in)
    return APIResponse(
        success=True,
        message=f"Wastage record '{item_code}' updated successfully.",
        data=item
    )
