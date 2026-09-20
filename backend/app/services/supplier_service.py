from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.all_models import Supplier, SupplierPerformance
from app.schemas.suppliers import SupplierOut, SupplierCreate, SupplierUpdate, SupplierRiskOut


class SupplierService:
    @staticmethod
    def _to_out(s: Supplier) -> SupplierOut:
        return SupplierOut(
            id=s.supplier_code,
            name=s.name,
            category=s.category,
            reliabilityScore=s.reliability_score,
            onTimeDelivery=s.on_time_delivery,
            leadTimeAvg=s.lead_time_avg,
            riskLevel=s.risk_level,
            status=s.status,
        )

    @staticmethod
    def get_all_suppliers(db: Session) -> List[SupplierOut]:
        suppliers = db.query(Supplier).all()
        return [SupplierService._to_out(s) for s in suppliers]

    @staticmethod
    def get_supplier_by_id(db: Session, supplier_code: str) -> SupplierOut:
        s = db.query(Supplier).filter(Supplier.supplier_code == supplier_code).first()
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Supplier '{supplier_code}' not found."
            )
        return SupplierService._to_out(s)

    @staticmethod
    def create_supplier(db: Session, s_in: SupplierCreate) -> SupplierOut:
        existing = db.query(Supplier).filter(Supplier.supplier_code == s_in.supplier_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with code '{s_in.supplier_code}' already exists."
            )
        
        sup = Supplier(
            supplier_code=s_in.supplier_code,
            name=s_in.name,
            category=s_in.category,
            reliability_score=s_in.reliability_score or "90.0%",
            on_time_delivery=s_in.on_time_delivery or "90.0%",
            lead_time_avg=s_in.lead_time_avg or "1.5 days",
            risk_level=s_in.risk_level or "LOW",
            status=s_in.status or "VERIFIED"
        )
        db.add(sup)
        db.commit()
        db.refresh(sup)
        return SupplierService._to_out(sup)

    @staticmethod
    def update_supplier(db: Session, supplier_code: str, s_in: SupplierUpdate) -> SupplierOut:
        sup = db.query(Supplier).filter(Supplier.supplier_code == supplier_code).first()
        if not sup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Supplier '{supplier_code}' not found."
            )
        
        update_data = s_in.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(sup, field, val)
        
        db.commit()
        db.refresh(sup)
        return SupplierService._to_out(sup)

    @staticmethod
    def delete_supplier(db: Session, supplier_code: str) -> dict:
        sup = db.query(Supplier).filter(Supplier.supplier_code == supplier_code).first()
        if not sup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Supplier '{supplier_code}' not found."
            )
        db.delete(sup)
        db.commit()
        return {"success": True, "message": f"Supplier '{supplier_code}' deleted successfully."}

    @staticmethod
    def get_reliability_scores(db: Session) -> List[dict]:
        suppliers = db.query(Supplier).all()
        return [
            {
                "supplier_id": s.supplier_code,
                "name": s.name,
                "reliability_score": s.reliability_score,
                "on_time_delivery": s.on_time_delivery,
            }
            for s in suppliers
        ]

    @staticmethod
    def get_lead_time_analysis(db: Session) -> List[dict]:
        suppliers = db.query(Supplier).all()
        return [
            {
                "supplier_id": s.supplier_code,
                "name": s.name,
                "lead_time_avg": s.lead_time_avg,
                "category": s.category,
            }
            for s in suppliers
        ]

    @staticmethod
    def get_supplier_risks(db: Session) -> List[SupplierRiskOut]:
        suppliers = db.query(Supplier).all()
        risks = []
        for s in suppliers:
            if s.risk_level != "LOW" or "Solapur" in s.name:
                risks.append(
                    SupplierRiskOut(
                        supplier_id=s.supplier_code,
                        supplier_name=s.name,
                        risk_level=s.risk_level,
                        impact_area=s.category,
                        mitigation_suggestion=f"Reallocate 25% purchase volume from {s.name} to secondary backup supplier."
                    )
                )
        return risks
