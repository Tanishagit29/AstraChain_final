from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.all_models import Wastage, Inventory, Product
from app.schemas.wastage import WastageItemOut, WastageCreate, WastageUpdate, DiscountRecommendationOut
from app.services.rio_mart_intelligence import NEAR_EXPIRY_MAX_DAYS, discount_pct_for_days


def _parse_currency_float(val_str: str) -> float:
    """Helper to convert string currency e.g. '₹120' to float."""
    import re
    if not val_str:
        return 0.0
    s = re.sub(r'[^\d\.]', '', str(val_str))
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


class WastageService:
    @staticmethod
    def _to_out(w: Wastage) -> WastageItemOut:
        return WastageItemOut(
            id=w.item_code,
            product=w.product,
            batch=w.batch,
            quantity=w.quantity,
            reason=w.reason,
            lossAmount=w.loss_amount,
            severity=w.severity,
            agentIntervention=w.agent_intervention or "Automated monitoring active",
        )

    @staticmethod
    def get_all_wastage(db: Session) -> List[WastageItemOut]:
        items = db.query(Wastage).all()
        return [WastageService._to_out(w) for w in items]

    @staticmethod
    def get_near_expiry_items(db: Session) -> List[WastageItemOut]:
        # CRITICAL rows are already-expired batches; this list is only for items that can still be sold.
        items = db.query(Wastage).filter(Wastage.severity.in_(["HIGH", "MEDIUM"])).all()
        return [WastageService._to_out(w) for w in items]

    @staticmethod
    def create_wastage_item(db: Session, w_in: WastageCreate) -> WastageItemOut:
        existing = db.query(Wastage).filter(Wastage.item_code == w_in.item_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Wastage record with code '{w_in.item_code}' already exists."
            )
        
        w_item = Wastage(
            item_code=w_in.item_code,
            product=w_in.product,
            batch=w_in.batch,
            quantity=w_in.quantity,
            reason=w_in.reason,
            loss_amount=w_in.loss_amount,
            severity=w_in.severity or "MEDIUM",
            agent_intervention=w_in.agent_intervention
        )
        db.add(w_item)
        db.commit()
        db.refresh(w_item)
        return WastageService._to_out(w_item)

    @staticmethod
    def update_wastage_item(db: Session, item_code: str, w_in: WastageUpdate) -> WastageItemOut:
        w_item = db.query(Wastage).filter(Wastage.item_code == item_code).first()
        if not w_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wastage record '{item_code}' not found."
            )
        
        update_data = w_in.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(w_item, field, val)
        
        db.commit()
        db.refresh(w_item)
        return WastageService._to_out(w_item)

    @staticmethod
    def get_discount_recommendations(db: Session) -> List[DiscountRecommendationOut]:
        """
        Recommendations for products that are NEAR expiry (0 <= days <= NEAR_EXPIRY_MAX_DAYS).
        Discount tiers are shared with the Rio Mart dataset: 50% <=2d, 30% <=5d, 20% <=7d, 10% <=10d.
        Already-expired products are never recommended for a discount. Most urgent first.
        """
        now_date = datetime.now(timezone.utc).date()
        products = db.query(Product).filter(Product.expiry_date.isnot(None)).all()
        batch_by_code = {w.item_code: w.batch for w in db.query(Wastage.item_code, Wastage.batch).all()}
        inv_by_product = {i.product_id: i for i in db.query(Inventory).filter(Inventory.product_id.isnot(None)).all()}
        lift_by_pct = {
            50: "+65% volume clearance lift",
            30: "+40% volume lift",
            20: "+25% volume lift",
            10: "+15% volume lift",
        }
        recs = []

        for prod in products:
            exp_date = prod.expiry_date.date() if isinstance(prod.expiry_date, datetime) else prod.expiry_date
            days = (exp_date - now_date).days
            if not (0 <= days <= NEAR_EXPIRY_MAX_DAYS):
                continue

            pct = discount_pct_for_days(days)
            inv = inv_by_product.get(prod.id)
            cost_str = inv.unit_cost if inv else prod.unit_cost
            batch = batch_by_code.get(f"WS-{prod.sku}") or f"B-{sum(map(ord, prod.sku)) % 900 + 100}"
            recs.append(
                DiscountRecommendationOut(
                    product_name=prod.name,
                    batch=batch,
                    days_to_expiry=days,
                    current_price=cost_str,
                    recommended_discount=f"{pct}% dynamic promo discount",
                    expected_sales_lift=lift_by_pct.get(pct, "+15% volume lift"),
                )
            )
        recs.sort(key=lambda r: r.days_to_expiry)
        return recs

    @staticmethod
    def get_expected_waste(db: Session) -> dict:
        items = db.query(Wastage).all()
        total_loss = 0.0
        categories = {}
        
        for w in items:
            loss_val = _parse_currency_float(w.loss_amount)
            total_loss += loss_val

        # Find top risk category from inventory
        top_cat = "General"
        near_exp_inv = db.query(Inventory).filter(Inventory.days_remaining <= 7).all()
        for item in near_exp_inv:
            categories[item.category] = categories.get(item.category, 0) + 1
        if categories:
            top_cat = max(categories, key=categories.get)

        return {
            "total_expected_loss_inr": f"₹{total_loss:,.0f}",
            "at_risk_batch_count": len(items),
            "projected_salvage_value": f"₹{total_loss * 0.55:,.0f}",
            "top_risk_category": top_cat
        }

