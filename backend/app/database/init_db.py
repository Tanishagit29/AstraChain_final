from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.session import engine
from app.core.security import get_password_hash
from app.models.all_models import (
    User, Category, Product, Inventory, Forecast,
    Supplier, Route, Wastage, AutomationLog, AgentActivity, Report
)

def init_db(db: Session) -> None:
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Safe migration: ensure expiry_date column exists in products table
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN expiry_date DATETIME;"))
            conn.commit()
    except Exception:
        # Column already exists
        pass

    # Seed User
    if not db.query(User).filter(User.email == "operator@transitops.ai").first():
        user = User(
            email="operator@transitops.ai",
            hashed_password=get_password_hash("TransitOps2026!"),
            full_name="Daksh Mehta",
            role="CHIEF_OPERATIONS_OFFICER",
            is_active=True
        )
        db.add(user)

    # Seed Inventory
    if db.query(Inventory).count() == 0:
        inventory_items = [
            Inventory(product_code="MK-001-F", name="Fresh Milk 1L", category="Dairy", current_stock=820, forecast_demand=1250, days_remaining=8, progress=25, risk="HIGH", action="Reorder 500 units", warehouse="Mumbai Central", unit_cost="₹54"),
            Inventory(product_code="RC-505-B", name="Basmati Rice 5kg", category="Staples", current_stock=2400, forecast_demand=1800, days_remaining=32, progress=80, risk="LOW", action="No action required", warehouse="Pune North", unit_cost="₹420"),
            Inventory(product_code="YG-500-D", name="Yogurt 500g", category="Dairy", current_stock=320, forecast_demand=450, days_remaining=4, progress=15, risk="HIGH", action="Apply 15% discount", warehouse="Thane East", unit_cost="₹65"),
            Inventory(product_code="OL-100-S", name="Sunflower Oil 1L", category="Staples", current_stock=1850, forecast_demand=1200, days_remaining=45, progress=90, risk="OVERSTOCK", action="Reduce next order", warehouse="Mumbai Central", unit_cost="₹145"),
            Inventory(product_code="AP-200-O", name="Organic Apples 1kg", category="Produce", current_stock=450, forecast_demand=600, days_remaining=6, progress=20, risk="HIGH", action="Expedite shipment", warehouse="Nashik Hub", unit_cost="₹180"),
            Inventory(product_code="BT-100-M", name="Amul Butter 500g", category="Dairy", current_stock=1100, forecast_demand=950, days_remaining=18, progress=60, risk="HEALTHY", action="Optimal level", warehouse="Pune North", unit_cost="₹275"),
            Inventory(product_code="CH-050-P", name="Cheddar Cheese 200g", category="Dairy", current_stock=680, forecast_demand=620, days_remaining=22, progress=70, risk="HEALTHY", action="Optimal level", warehouse="Mumbai Central", unit_cost="₹160"),
            Inventory(product_code="TM-100-F", name="Fresh Tomatoes 1kg", category="Produce", current_stock=290, forecast_demand=700, days_remaining=3, progress=10, risk="HIGH", action="Local emergency buy", warehouse="Thane East", unit_cost="₹35"),
        ]
        db.add_all(inventory_items)

    # Seed Demand Forecasts
    if db.query(Forecast).count() == 0:
        forecast_items = [
            Forecast(day="Oct 18", historical=320, forecast=320, confidence_upper=340, confidence_lower=300),
            Forecast(day="Oct 19", historical=340, forecast=340, confidence_upper=365, confidence_lower=315),
            Forecast(day="Oct 20", historical=310, forecast=310, confidence_upper=330, confidence_lower=290),
            Forecast(day="Oct 21", historical=360, forecast=360, confidence_upper=385, confidence_lower=335),
            Forecast(day="Oct 22", historical=380, forecast=380, confidence_upper=410, confidence_lower=350),
            Forecast(day="Oct 23", historical=410, forecast=410, confidence_upper=440, confidence_lower=380),
            Forecast(day="Oct 24", historical=450, forecast=450, confidence_upper=480, confidence_lower=420),
            Forecast(day="Oct 25", forecast=480, confidence_upper=520, confidence_lower=440),
            Forecast(day="Oct 26", forecast=510, confidence_upper=560, confidence_lower=460),
            Forecast(day="Oct 27", forecast=530, confidence_upper=580, confidence_lower=480),
            Forecast(day="Oct 28", forecast=490, confidence_upper=540, confidence_lower=440),
            Forecast(day="Oct 29", forecast=520, confidence_upper=570, confidence_lower=470),
            Forecast(day="Oct 30", forecast=560, confidence_upper=610, confidence_lower=500),
        ]
        db.add_all(forecast_items)

    # Seed Suppliers
    if db.query(Supplier).count() == 0:
        suppliers = [
            Supplier(supplier_code="SUP-01", name="Amul Dairy Cooperatives", category="Dairy", reliability_score="98.4%", on_time_delivery="96.2%", lead_time_avg="1.2 days", risk_level="LOW", status="VERIFIED"),
            Supplier(supplier_code="SUP-02", name="Maharashtra Grain Processors", category="Staples", reliability_score="92.1%", on_time_delivery="89.5%", lead_time_avg="3.4 days", risk_level="MEDIUM", status="VERIFIED"),
            Supplier(supplier_code="SUP-03", name="Sahyadri Farms Fresh", category="Produce", reliability_score="94.8%", on_time_delivery="95.0%", lead_time_avg="0.8 days", risk_level="LOW", status="VERIFIED"),
            Supplier(supplier_code="SUP-04", name="Solapur Edible Oils Ltd", category="Staples", reliability_score="81.5%", on_time_delivery="78.0%", lead_time_avg="4.5 days", risk_level="HIGH", status="UNDER_REVIEW"),
        ]
        db.add_all(suppliers)

    # Seed Routes
    if db.query(Route).count() == 0:
        routes = [
            Route(route_code="RT-8841", truck_id="MH-04-JK-4821", driver="Rajesh Kumar", origin="Mumbai Central Port", destination="Pune Logistics Hub", status="IN_TRANSIT", eta="14:35 (On Time)", temp="3.2°C", fuel_saved="₹1,850", risk="LOW"),
            Route(route_code="RT-9204", truck_id="MH-12-PQ-9102", driver="Suresh Patil", origin="Nashik Warehouse", destination="Thane Cold Storage", status="DELAYED", eta="16:20 (+25m NH-48 Traffic)", temp="4.1°C", fuel_saved="₹920", risk="MEDIUM"),
            Route(route_code="RT-7712", truck_id="MH-46-AB-3301", driver="Amit Shinde", origin="Pune North Hub", destination="Solapur Distribution", status="IN_TRANSIT", eta="18:00 (On Time)", temp="2.8°C", fuel_saved="₹2,400", risk="OPTIMAL"),
            Route(route_code="RT-6019", truck_id="MH-02-CD-5541", driver="Vikram Singh", origin="Surat Port Depot", destination="Mumbai Central", status="REROUTED", eta="15:10 (Auto-adjusted)", temp="3.5°C", fuel_saved="₹3,100", risk="AI_REROUTED"),
        ]
        db.add_all(routes)

    # Seed Wastage
    if db.query(Wastage).count() == 0:
        wastage_items = [
            Wastage(item_code="WS-401", product="Fresh Milk 1L", batch="B-884-21", quantity="120 L", reason="Cold chain temp spike (4.8°C)", loss_amount="₹6,480", severity="HIGH", agent_intervention="Temp adjusted remotely by Wastage Agent"),
            Wastage(item_code="WS-402", product="Organic Strawberries", batch="B-912-04", quantity="45 kg", reason="Shelf-life expiry near", loss_amount="₹13,500", severity="MEDIUM", agent_intervention="15% dynamic promo auto-applied"),
            Wastage(item_code="WS-403", product="Greek Yogurt 200g", batch="B-771-09", quantity="80 units", reason="Packaging seal breach", loss_amount="₹5,200", severity="LOW", agent_intervention="Supplier quality claim opened"),
        ]
        db.add_all(wastage_items)

    # Seed Automation Logs / Rules
    if db.query(AutomationLog).count() == 0:
        rules = [
            AutomationLog(rule_code="AUT-101", name="Automated Stockout Reorder", trigger="Stock < 10 days of forecast demand", action="Generate Purchase Intent & Notify Operations Lead", status="ENABLED", executions_today=14),
            AutomationLog(rule_code="AUT-102", name="Cold Chain Thermal Guardrail", trigger="Truck Temp variance > 1.5°C for 10 minutes", action="Send remote HVAC override command + alert driver", status="ENABLED", executions_today=3),
            AutomationLog(rule_code="AUT-103", name="Dynamic Markdown for Near-Expiry", trigger="Perishable item expiry <= 5 days & stock > 50 units", action="Apply 15% discount on POS & E-commerce channels", status="ENABLED", executions_today=8),
            AutomationLog(rule_code="AUT-104", name="Congestion Reroute Trigger", trigger="Route delay estimate > 20 minutes", action="Auto-calculate alternate highway route & update GPS telemetry", status="ENABLED", executions_today=12),
        ]
        db.add_all(rules)

    # Seed Agent Activities
    if db.query(AgentActivity).count() == 0:
        activities = [
            AgentActivity(agent_code="AG-01", agent="Forecast Agent", role="Predictive Analytics & Seasonal Spikes", status="ACTIVE", confidence="94%", tasks_processed=14280, latency="14ms", action="updated regional demand models for Q4.", details="Successfully adjusted for seasonal Diwali spikes in Northern regions.", time_ago="2m ago", color="primary"),
            AgentActivity(agent_code="AG-02", agent="Inventory Agent", role="Stockout Guard & Safety Stock Optimizer", status="ACTIVE", confidence="96%", tasks_processed=28910, latency="8ms", action="flagged stockout risk for 3 SKUs.", details="Affected warehouses: Mumbai Central, Pune North.", time_ago="14m ago", color="tertiary"),
            AgentActivity(agent_code="AG-03", agent="Wastage Agent", role="Perishable Monitoring & Dynamic Discounting", status="ACTIVE", confidence="91%", tasks_processed=9450, latency="22ms", action="optimized cold chain transit temps.", details="Detected 2°C variance in Truck ID: TS-442; corrected remotely.", time_ago="45m ago", color="secondary"),
            AgentActivity(agent_code="AG-04", agent="Route Agent", role="Traffic Rerouting & Fuel Economy", status="ACTIVE", confidence="98%", tasks_processed=18200, latency="11ms", action="rerouted 12 shipments due to NH-48 closure.", details="Estimated ETA delay: 15 mins. Saved ₹24k in fuel costs.", time_ago="1h ago", color="primary-container"),
        ]
        db.add_all(activities)

    # Seed Reports
    if db.query(Report).count() == 0:
        reports = [
            Report(report_code="REP-01", title="Q4 Supply Chain Efficiency & Cost Savings", date="Oct 24, 2024", type="Executive Summary", author="Copilot AI & Daksh Mehta", size="2.4 MB"),
            Report(report_code="REP-02", title="Perishable Wastage Audit & Thermal Telemetry", date="Oct 20, 2024", type="Operations Report", author="Wastage Prevention Agent", size="1.8 MB"),
            Report(report_code="REP-03", title="Regional Warehouse Capacity & Stockout Risk", date="Oct 15, 2024", type="Inventory Intelligence", author="Inventory Agent", size="4.1 MB"),
        ]
        db.add_all(reports)

    # Seed Rio Mart Unified Data if not already present
    try:
        from app.database.seed_rio_mart import seed_rio_mart_data
        rio_inventory = db.query(Inventory).filter(Inventory.product_code.like("RIO-%")).count()
        rio_expiry_rows = db.query(Product).filter(Product.sku.like("RIO-%"), Product.expiry_date.isnot(None)).count()
        # Seed on first run; also upgrade databases seeded by the older version, which stored
        # raw STOCKOUT/CRITICAL labels, had no OVERSTOCK items and no expiry dates for the Wastage Agent.
        if rio_inventory == 0 or rio_expiry_rows == 0:
            seed_rio_mart_data(db, max_records_per_store=50)
    except Exception as e:
        from app.core.logging import logger
        logger.warning(f"Skipped auto-seeding Rio Mart data during init_db: {e}")

    db.commit()

