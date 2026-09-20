from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.all_models import Report, Product, Inventory, Supplier, Wastage, SalesHistory
from app.schemas.reports import ReportOut, ReportGenerateRequest


class ReportService:
    @staticmethod
    def get_reports(db: Session) -> List[ReportOut]:
        reports = db.query(Report).all()
        return [
            ReportOut(
                id=r.report_code,
                title=r.title,
                date=r.date,
                type=r.type,
                author=r.author,
                size=r.size,
            )
            for r in reports
        ]

    @staticmethod
    def generate_report(db: Session, req: ReportGenerateRequest) -> ReportOut:
        now_str = datetime.now(timezone.utc).strftime("%b %d, %Y")
        code = f"REP-0{db.query(Report).count() + 1}"

        new_report = Report(
            report_code=code,
            title=req.title or f"{req.report_type} Supply Chain Intelligence Audit",
            date=now_str,
            type=req.report_type or "Executive Summary",
            author="Copilot AI",
            size="2.4 MB"
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

        return ReportOut(
            id=new_report.report_code,
            title=new_report.title,
            date=new_report.date,
            type=new_report.type,
            author=new_report.author,
            size=new_report.size
        )

    @staticmethod
    def get_weekly_report_data(db: Session) -> Dict[str, Any]:
        return {
            "period": "Weekly Audit (Oct 18 - Oct 25)",
            "total_products_monitored": db.query(Product).count(),
            "stockout_risks_resolved": db.query(Inventory).filter(Inventory.risk == "HIGH").count(),
            "suppliers_audited": db.query(Supplier).count(),
            "wastage_loss_averted_inr": "₹42,500",
            "overall_health_score": "88.4%"
        }

    @staticmethod
    def get_monthly_report_data(db: Session) -> Dict[str, Any]:
        return {
            "period": "Monthly Executive Report (October 2024)",
            "total_sales_revenue": "₹24.8M",
            "forecast_accuracy": "94.2%",
            "route_fuel_savings": "₹18,500",
            "inventory_turnover_ratio": "4.8x",
            "overall_health_score": "91.0%"
        }

    @staticmethod
    def export_report_json(db: Session, report_code: str) -> Dict[str, Any]:
        rep = db.query(Report).filter(Report.report_code == report_code).first()
        return {
            "report_id": report_code,
            "title": rep.title if rep else "Supply Chain Report",
            "type": rep.type if rep else "Audit",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": ReportService.get_weekly_report_data(db)
        }
