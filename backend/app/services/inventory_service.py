import math
from typing import List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.all_models import Inventory, SalesHistory, Product, Supplier
from app.schemas.inventory import (
    InventoryItemOut, InventoryItemCreate, InventoryItemUpdate,
    InventoryPaginatedOut, ReorderRecommendationOut
)


class InventoryService:
    @staticmethod
    def _calculate_metrics(db: Session, item: Inventory) -> Tuple[int, int, float, float]:
        """Calculates Safety Stock, Reorder Point, Avg Daily Demand, and Stockout Probability."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # 1. Average Daily Demand from Sales History
        sales_records = []
        if item.product_id:
            sales_records = db.query(SalesHistory.quantity).filter(
                SalesHistory.product_id == item.product_id,
                SalesHistory.timestamp >= thirty_days_ago
            ).all()

        quantities = [r[0] for r in sales_records] if sales_records else [max(10, item.forecast_demand // 30)]
        avg_demand = sum(quantities) / max(len(quantities), 1)

        # Standard deviation of demand
        variance = sum((q - avg_demand) ** 2 for q in quantities) / max(len(quantities), 1)
        std_dev = math.sqrt(variance) if variance > 0 else avg_demand * 0.2

        # Lead time default (days)
        lead_time = 2.0
        if "Dairy" in item.category or "Produce" in item.category:
            lead_time = 1.0
        elif "Staples" in item.category:
            lead_time = 3.5

        # Safety Stock formula (95% confidence level Z = 1.65)
        safety_stock = int(math.ceil(1.65 * std_dev * math.sqrt(lead_time)))
        reorder_point = int(math.ceil(avg_demand * lead_time)) + safety_stock

        # Stockout Probability calculation
        if item.current_stock <= 0:
            stockout_prob = 0.99
        elif item.current_stock < reorder_point:
            deficit_ratio = (reorder_point - item.current_stock) / max(reorder_point, 1)
            stockout_prob = min(0.95, round(0.40 + (deficit_ratio * 0.55), 2))
        else:
            stockout_prob = max(0.05, round(0.10 - ((item.current_stock - reorder_point) / (reorder_point * 5)), 2))

        return safety_stock, reorder_point, round(avg_demand, 1), stockout_prob

    @staticmethod
    def _to_out(db: Session, item: Inventory) -> InventoryItemOut:
        safety_stock, reorder_point, avg_demand, stockout_prob = InventoryService._calculate_metrics(db, item)
        return InventoryItemOut(
            id=item.product_code,
            name=item.name,
            category=item.category,
            currentStock=item.current_stock,
            forecastDemand=item.forecast_demand,
            daysRemaining=item.days_remaining,
            progress=item.progress,
            risk=item.risk,
            action=item.action or "Optimal level",
            warehouse=item.warehouse,
            unitCost=item.unit_cost,
            safetyStock=safety_stock,
            reorderPoint=reorder_point,
            avgDailyDemand=avg_demand,
            stockoutProbability=stockout_prob
        )

    @staticmethod
    def get_all_inventory(
        db: Session,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        category: Optional[str] = None,
        warehouse: Optional[str] = None,
        risk: Optional[str] = None
    ) -> InventoryPaginatedOut:
        query = db.query(Inventory)

        if search:
            query = query.filter(Inventory.name.ilike(f"%{search}%") | Inventory.product_code.ilike(f"%{search}%"))
        if category:
            query = query.filter(Inventory.category.ilike(f"%{category}%"))
        if warehouse:
            query = query.filter(Inventory.warehouse.ilike(f"%{warehouse}%"))
        if risk:
            query = query.filter(Inventory.risk == risk.upper())

        total = query.count()
        pages = math.ceil(total / max(limit, 1))
        offset = (page - 1) * limit
        items = query.offset(offset).limit(limit).all()

        out_items = [InventoryService._to_out(db, item) for item in items]

        return InventoryPaginatedOut(
            items=out_items,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )

    @staticmethod
    def get_inventory_item(db: Session, product_code: str) -> InventoryItemOut:
        item = db.query(Inventory).filter(Inventory.product_code == product_code).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item '{product_code}' not found."
            )
        return InventoryService._to_out(db, item)

    @staticmethod
    def create_inventory_item(db: Session, item_in: InventoryItemCreate) -> InventoryItemOut:
        existing = db.query(Inventory).filter(Inventory.product_code == item_in.product_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inventory item with code '{item_in.product_code}' already exists."
            )
        
        prod = db.query(Product).filter(Product.sku == item_in.product_code).first()
        db_item = Inventory(
            product_code=item_in.product_code,
            name=item_in.name,
            category=item_in.category,
            current_stock=item_in.current_stock,
            forecast_demand=item_in.forecast_demand,
            days_remaining=item_in.days_remaining,
            progress=item_in.progress or 50,
            risk=item_in.risk or "HEALTHY",
            action=item_in.action or "Optimal level",
            warehouse=item_in.warehouse or "Mumbai Central",
            unit_cost=item_in.unit_cost,
            product_id=prod.id if prod else None
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return InventoryService._to_out(db, db_item)

    @staticmethod
    def update_inventory_item(db: Session, product_code: str, item_in: InventoryItemUpdate) -> InventoryItemOut:
        item = db.query(Inventory).filter(Inventory.product_code == product_code).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item '{product_code}' not found."
            )
        
        update_data = item_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        db.commit()
        db.refresh(item)
        return InventoryService._to_out(db, item)

    @staticmethod
    def delete_inventory_item(db: Session, product_code: str) -> dict:
        item = db.query(Inventory).filter(Inventory.product_code == product_code).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item '{product_code}' not found."
            )
        db.delete(item)
        db.commit()
        return {"success": True, "message": f"Inventory item '{product_code}' deleted successfully."}

    @staticmethod
    def get_low_stock_items(db: Session) -> List[InventoryItemOut]:
        items = db.query(Inventory).filter(Inventory.days_remaining <= 7).all()
        return [InventoryService._to_out(db, item) for item in items]

    @staticmethod
    def get_stockout_risk_items(db: Session) -> List[InventoryItemOut]:
        items = db.query(Inventory).filter(Inventory.risk == "HIGH").all()
        return [InventoryService._to_out(db, item) for item in items]

    @staticmethod
    def get_overstock_risk_items(db: Session) -> List[InventoryItemOut]:
        items = db.query(Inventory).filter(Inventory.risk == "OVERSTOCK").all()
        return [InventoryService._to_out(db, item) for item in items]

    @staticmethod
    def get_reorder_recommendations(db: Session) -> List[ReorderRecommendationOut]:
        # Reorders are for items that are running out. OVERSTOCK items need the opposite
        # (reduce / pause the next order), so they are deliberately not listed here.
        items = db.query(Inventory).filter(Inventory.risk.in_(["HIGH", "MEDIUM"])).all()
        reorders = []
        
        suppliers = db.query(Supplier).all()
        supplier_map = {s.category: s.name for s in suppliers}

        for item in items:
            safety_stock, reorder_point, avg_demand, _ = InventoryService._calculate_metrics(db, item)
            needed = max(500, (reorder_point - item.current_stock) + int(avg_demand * 14))
            
            assigned_supplier = supplier_map.get(item.category, "Amul Dairy Cooperatives")
            urgency = "HIGH" if item.days_remaining <= 4 else ("MEDIUM" if item.days_remaining <= 8 else "LOW")
            
            reorders.append(
                ReorderRecommendationOut(
                    product_id=item.product_code,
                    product_name=item.name,
                    current_stock=item.current_stock,
                    safety_stock=safety_stock,
                    reorder_point=reorder_point,
                    suggested_reorder_qty=needed,
                    supplier=assigned_supplier,
                    urgency=urgency
                )
            )
        return reorders
