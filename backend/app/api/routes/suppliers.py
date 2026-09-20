from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.suppliers import SupplierOut, SupplierCreate, SupplierUpdate, SupplierRiskOut
from app.services.supplier_service import SupplierService
from app.api.deps import get_current_user
from app.models.all_models import User

router = APIRouter(prefix="/suppliers", tags=["Supplier Intelligence"])


@router.get("", response_model=APIResponse[List[SupplierOut]])
def get_all_suppliers(db: Session = Depends(get_db)):
    suppliers = SupplierService.get_all_suppliers(db)
    return APIResponse(
        success=True,
        message="Suppliers retrieved successfully.",
        data=suppliers
    )


@router.get("/reliability", response_model=APIResponse[List[dict]])
def get_reliability_scores(db: Session = Depends(get_db)):
    scores = SupplierService.get_reliability_scores(db)
    return APIResponse(
        success=True,
        message="Supplier reliability scores retrieved.",
        data=scores
    )


@router.get("/lead-time", response_model=APIResponse[List[dict]])
def get_lead_time_analysis(db: Session = Depends(get_db)):
    lead_times = SupplierService.get_lead_time_analysis(db)
    return APIResponse(
        success=True,
        message="Supplier lead time analysis retrieved.",
        data=lead_times
    )


@router.get("/risk", response_model=APIResponse[List[SupplierRiskOut]])
def get_supplier_risks(db: Session = Depends(get_db)):
    risks = SupplierService.get_supplier_risks(db)
    return APIResponse(
        success=True,
        message="Supplier risk evaluations retrieved.",
        data=risks
    )


@router.get("/{supplier_code}", response_model=APIResponse[SupplierOut])
def get_supplier(supplier_code: str, db: Session = Depends(get_db)):
    supplier = SupplierService.get_supplier_by_id(db, supplier_code)
    return APIResponse(
        success=True,
        message=f"Supplier '{supplier_code}' retrieved successfully.",
        data=supplier
    )


@router.post("", response_model=APIResponse[SupplierOut], status_code=status.HTTP_201_CREATED)
def create_supplier(
    s_in: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    supplier = SupplierService.create_supplier(db, s_in)
    return APIResponse(
        success=True,
        message=f"Supplier '{s_in.supplier_code}' created successfully.",
        data=supplier
    )


@router.put("/{supplier_code}", response_model=APIResponse[SupplierOut])
def update_supplier(
    supplier_code: str,
    s_in: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    supplier = SupplierService.update_supplier(db, supplier_code, s_in)
    return APIResponse(
        success=True,
        message=f"Supplier '{supplier_code}' updated successfully.",
        data=supplier
    )


@router.delete("/{supplier_code}", response_model=APIResponse[dict])
def delete_supplier(
    supplier_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = SupplierService.delete_supplier(db, supplier_code)
    return APIResponse(
        success=True,
        message=f"Supplier '{supplier_code}' deleted successfully.",
        data=result
    )
