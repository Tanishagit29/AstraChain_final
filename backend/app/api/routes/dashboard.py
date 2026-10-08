from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.dashboard import DashboardSummaryOut
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("", response_model=APIResponse[DashboardSummaryOut])
def get_dashboard_data(db: Session = Depends(get_db)):
    summary = DashboardService.get_dashboard_summary(db)
    return APIResponse(
        success=True,
        message="Dashboard summary metrics retrieved successfully.",
        data=summary
    )
