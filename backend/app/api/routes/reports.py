from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.reports import ReportOut, ReportGenerateRequest
from app.services.report_service import ReportService
from app.api.deps import get_current_user
from app.models.all_models import User

router = APIRouter(prefix="/reports", tags=["Reports & Insights"])


@router.get("", response_model=APIResponse[List[ReportOut]])
def get_reports(db: Session = Depends(get_db)):
    reports = ReportService.get_reports(db)
    return APIResponse(
        success=True,
        message="Reports retrieved successfully.",
        data=reports
    )


@router.get("/weekly", response_model=APIResponse[dict])
def get_weekly_report(db: Session = Depends(get_db)):
    data = ReportService.get_weekly_report_data(db)
    return APIResponse(
        success=True,
        message="Weekly supply chain report generated.",
        data=data
    )


@router.get("/monthly", response_model=APIResponse[dict])
def get_monthly_report(db: Session = Depends(get_db)):
    data = ReportService.get_monthly_report_data(db)
    return APIResponse(
        success=True,
        message="Monthly supply chain executive summary generated.",
        data=data
    )


@router.post("/export", response_model=APIResponse[dict])
def export_report(req: ReportGenerateRequest, db: Session = Depends(get_db)):
    report_out = ReportService.generate_report(db, req)
    export_data = ReportService.export_report_json(db, report_out.id)
    return APIResponse(
        success=True,
        message=f"Report '{report_out.id}' exported successfully.",
        data=export_data
    )


@router.post("/generate", response_model=APIResponse[ReportOut], status_code=status.HTTP_201_CREATED)
def generate_report(
    req: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report_out = ReportService.generate_report(db, req)
    return APIResponse(
        success=True,
        message="New report generated successfully.",
        data=report_out
    )
