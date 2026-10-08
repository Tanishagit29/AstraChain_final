from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.rio_mart_service import RioMartService
from app.database.seed_rio_mart import seed_rio_mart_data

router = APIRouter(prefix="/rio-mart", tags=["Rio Mart Intelligence & Unified Dataset"])


@router.get("/summary", summary="Get Rio Mart Unified Dataset Summary Statistics")
def get_rio_mart_summary():
    """Returns high-level statistics for the Rio Mart 281k unified CSV dataset."""
    try:
        return RioMartService.get_summary()
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error reading Rio Mart dataset: {str(e)}")


@router.get("/stores", summary="Get Rio Mart Store Network & Locations")
def get_rio_mart_stores():
    """Returns store locations, demand weights, and daily delivery stats."""
    try:
        return RioMartService.get_stores()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/inventory", summary="Query Rio Mart Inventory & Stock (281k+ Records)")
def get_rio_mart_inventory(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    search: Optional[str] = Query(None, description="Search product name, code or category"),
    store_id: Optional[str] = Query(None, description="Filter by store ID (e.g. ST01, ST02)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    risk: Optional[str] = Query(None, description="Filter by stock status (STOCKOUT, CRITICAL, AT_RISK, HEALTHY, OVERSTOCK)"),
    is_perishable: Optional[bool] = Query(None, description="Filter perishable items"),
    festival: Optional[str] = Query(None, description="Filter by festival group or upcoming festival")
):
    """Paginated real-time search and filter across all 281,660 Rio Mart SKU records."""
    try:
        return RioMartService.get_inventory(
            page=page,
            limit=limit,
            search=search,
            store_id=store_id,
            category=category,
            risk=risk,
            is_perishable=is_perishable,
            festival=festival
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/festivals", summary="Get Festival Demand Multipliers & Impact")
def get_rio_mart_festivals():
    """Returns festival-wise demand impact analysis based on Rio Mart dataset."""
    try:
        return RioMartService.get_festivals_impact()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/inventory-agent", summary="Inventory Agent view: stockout AND overstock items")
def get_rio_mart_inventory_agent():
    """
    Prioritised stockout-risk (STOCKOUT/CRITICAL) and overstock items, plus low-stock and optimal
    examples, with dataset-wide counts. This is the same data the Inventory Intelligence page shows.
    """
    try:
        return RioMartService.get_inventory_agent_view()
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/wastage-agent", summary="Wastage Agent view: near-expiry items with discounts")
def get_rio_mart_wastage_agent():
    """
    Near-expiry perishables balanced across discount tiers (50% <=2d, 30% <=5d, 20% <=7d, 10% <=10d),
    each with its markdown price. Expired products are never listed. Same data the Wastage page shows.
    """
    try:
        return RioMartService.get_wastage_agent_view()
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/wastage", summary="Get Near-Expiry Items With Recommended Discounts")
def get_rio_mart_wastage(limit: int = Query(50, ge=1, le=200)):
    """Returns near-expiry perishables (most urgent first) with their recommended discount across Rio Mart stores."""
    try:
        return RioMartService.get_wastage_risk_items(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/seed", summary="Seed Primary Database with Rio Mart Data")
def seed_database_from_rio_mart(
    max_per_store: int = Query(200, ge=10, le=1000, description="Max SKUs to seed per store"),
    db: Session = Depends(get_db)
):
    """Populates primary database (products, inventory, wastage) with real Rio Mart CSV data."""
    try:
        res = seed_rio_mart_data(db, max_records_per_store=max_per_store)
        return {
            "status": "success",
            "message": "Primary database seeded with Rio Mart Unified dataset records.",
            "details": res
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to seed database: {str(e)}")
