import sys
import os
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database.session import SessionLocal, engine
from app.database.base import Base
from app.core.security import get_password_hash
from app.models.all_models import (
    User, Category, Product, Inventory, SalesHistory, Forecast,
    Supplier, SupplierPerformance, Warehouse, Route, Delivery,
    Wastage, Notification, AutomationLog, AgentActivity, Report
)


def seed_database():
    db = SessionLocal()
    try:
        print("Starting TransitOps Idempotent Database Seeding...")

        # 1. Users
        if not db.query(User).filter(User.email == "operator@transitops.ai").first():
            db.add(User(
                email="operator@transitops.ai",
                hashed_password=get_password_hash("TransitOps2026!"),
                full_name="Daksh Mehta",
                role="CHIEF_OPERATIONS_OFFICER",
                is_active=True
            ))

        if not db.query(User).filter(User.email == "admin@transitops.ai").first():
            db.add(User(
                email="admin@transitops.ai",
                hashed_password=get_password_hash("AdminTransit2026!"),
                full_name="System Administrator",
                role="ADMIN",
                is_active=True
            ))
        db.commit()

        # 2. Warehouses
        warehouse_names = [
            ("Mumbai Central", "Port Highway Road, Mumbai", 75000),
            ("Pune North", "Chakan Industrial Zone, Pune", 60000),
            ("Thane East", "Cold Chain Terminal, Thane", 45000),
            ("Nashik Hub", "Agri Logistics Park, Nashik", 50000),
            ("Nagpur Park", "Central Transport Hub, Nagpur", 80000)
        ]
        for name, loc, cap in warehouse_names:
            if not db.query(Warehouse).filter(Warehouse.name == name).first():
                db.add(Warehouse(name=name, location=loc, capacity_sqft=cap))
        db.commit()

        # 3. Categories (10+)
        categories_data = [
            ("Dairy", "Fresh milk, cheese, yogurt, butter, and cream items"),
            ("Staples", "Rice, flour, pulses, edible oils, and grains"),
            ("Produce", "Fresh vegetables, fruits, and leafy greens"),
            ("Beverages", "Juices, bottled water, energy drinks, and tea/coffee"),
            ("Frozen Foods", "Ice creams, frozen snacks, and ready-to-cook meals"),
            ("Bakery", "Fresh bread, buns, cakes, and pastries"),
            ("Meat & Seafood", "Chilled chicken, mutton, and fresh ocean fish"),
            ("Personal Care", "Soaps, shampoos, toothpaste, and skincare"),
            ("Packaged Snacks", "Biscuits, chips, nuts, and chocolate confectionery"),
            ("Household Essentials", "Detergents, surface cleaners, and paper products")
        ]
        cat_map = {}
        for c_name, c_desc in categories_data:
            cat = db.query(Category).filter(Category.name == c_name).first()
            if not cat:
                cat = Category(name=c_name, description=c_desc)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cat_map[c_name] = cat.id

        # 4. Suppliers (8+)
        suppliers_data = [
            ("SUP-01", "Amul Dairy Cooperatives", "Dairy", "98.4%", "96.2%", "1.2 days", "LOW", "VERIFIED"),
            ("SUP-02", "Maharashtra Grain Processors", "Staples", "92.1%", "89.5%", "3.4 days", "MEDIUM", "VERIFIED"),
            ("SUP-03", "Sahyadri Farms Fresh", "Produce", "94.8%", "95.0%", "0.8 days", "LOW", "VERIFIED"),
            ("SUP-04", "Solapur Edible Oils Ltd", "Staples", "81.5%", "78.0%", "4.5 days", "HIGH", "UNDER_REVIEW"),
            ("SUP-05", "Godrej Agrovet Ltd", "Meat & Seafood", "91.0%", "92.5%", "1.8 days", "LOW", "VERIFIED"),
            ("SUP-06", "Britannia Foods Corp", "Bakery", "96.5%", "97.1%", "1.0 days", "LOW", "VERIFIED"),
            ("SUP-07", "Hindustan Beverages", "Beverages", "88.2%", "86.0%", "2.5 days", "MEDIUM", "VERIFIED"),
            ("SUP-08", "Apex Household Solutions", "Household Essentials", "95.0%", "94.2%", "1.5 days", "LOW", "VERIFIED")
        ]
        for code, sname, scat, rel, ontime, lead, srisk, sstatus in suppliers_data:
            if not db.query(Supplier).filter(Supplier.supplier_code == code).first():
                sup = Supplier(
                    supplier_code=code,
                    name=sname,
                    category=scat,
                    reliability_score=rel,
                    on_time_delivery=ontime,
                    lead_time_avg=lead,
                    risk_level=srisk,
                    status=sstatus
                )
                db.add(sup)
                db.commit()
                db.refresh(sup)
                # Performance log
                db.add(SupplierPerformance(
                    supplier_id=sup.id,
                    score=float(rel.replace('%', '')),
                    notes=f"Quarterly audit report for {sname}."
                ))
        db.commit()

        # 5. Products (30+)
        raw_products = [
            ("MK-001-F", "Fresh Milk 1L", "Dairy", 54, 8, "HIGH"),
            ("RC-505-B", "Basmati Rice 5kg", "Staples", 420, 32, "LOW"),
            ("YG-500-D", "Yogurt 500g", "Dairy", 65, 4, "HIGH"),
            ("OL-100-S", "Sunflower Oil 1L", "Staples", 145, 45, "OVERSTOCK"),
            ("AP-200-O", "Organic Apples 1kg", "Produce", 180, 6, "HIGH"),
            ("BT-100-M", "Amul Butter 500g", "Dairy", 275, 18, "HEALTHY"),
            ("CH-050-P", "Cheddar Cheese 200g", "Dairy", 160, 22, "HEALTHY"),
            ("TM-100-F", "Fresh Tomatoes 1kg", "Produce", 35, 3, "HIGH"),
            ("BR-400-W", "Whole Wheat Bread 400g", "Bakery", 45, 2, "HIGH"),
            ("CJ-100-A", "Alphonso Mango Juice 1L", "Beverages", 120, 25, "HEALTHY"),
            ("IC-500-V", "Vanilla Ice Cream 1L", "Frozen Foods", 210, 15, "HEALTHY"),
            ("CK-500-F", "Fresh Chicken Breast 500g", "Meat & Seafood", 195, 3, "HIGH"),
            ("SP-100-T", "Total Hygiene Soap 125g", "Personal Care", 40, 60, "HEALTHY"),
            ("BS-200-D", "Digestive Biscuits 200g", "Packaged Snacks", 35, 40, "HEALTHY"),
            ("DT-100-L", "Liquid Detergent 1L", "Household Essentials", 230, 50, "HEALTHY"),
            ("FL-100-A", "Atta Whole Wheat 10kg", "Staples", 380, 28, "HEALTHY"),
            ("PNT-200-R", "Roasted Peanuts 200g", "Packaged Snacks", 60, 35, "HEALTHY"),
            ("GR-100-G", "Green Tea Bags 100s", "Beverages", 290, 55, "HEALTHY"),
            ("CS-100-C", "Cottage Cheese Paneer 200g", "Dairy", 90, 5, "HIGH"),
            ("ON-100-R", "Red Onions 1kg", "Produce", 30, 12, "HEALTHY"),
            ("PT-100-O", "Organic Potatoes 1kg", "Produce", 28, 14, "HEALTHY"),
            ("FR-200-F", "Frozen Peas 500g", "Frozen Foods", 85, 30, "HEALTHY"),
            ("SH-200-A", "Anti-Dandruff Shampoo 200ml", "Personal Care", 185, 45, "HEALTHY"),
            ("TP-100-F", "Fresh Mint Toothpaste 150g", "Personal Care", 95, 50, "HEALTHY"),
            ("CF-100-I", "Instant Coffee 100g", "Beverages", 310, 40, "HEALTHY"),
            ("FC-500-N", "Fish Fillet Frozen 500g", "Meat & Seafood", 340, 7, "HIGH"),
            ("BUN-200-B", "Burger Buns 4s", "Bakery", 30, 2, "HIGH"),
            ("SC-100-S", "Surface Cleaner 500ml", "Household Essentials", 115, 60, "HEALTHY"),
            ("CH-100-D", "Dark Chocolate 100g", "Packaged Snacks", 150, 45, "HEALTHY"),
            ("ML-100-T", "Toned Milk 500ml", "Dairy", 28, 4, "HIGH")
        ]

        prod_map = {}
        for sku, name, cat_name, cost, days_rem, risk in raw_products:
            prod = db.query(Product).filter(Product.sku == sku).first()
            if not prod:
                prod = Product(
                    sku=sku,
                    name=name,
                    category_name=cat_name,
                    category_id=cat_map.get(cat_name),
                    unit_cost=f"₹{cost}",
                    days_remaining=days_rem,
                    risk_level=risk
                )
                db.add(prod)
                db.commit()
                db.refresh(prod)
            prod_map[sku] = prod

        # 6. Inventory Items
        warehouses = ["Mumbai Central", "Pune North", "Thane East", "Nashik Hub", "Nagpur Park"]
        for idx, (sku, name, cat_name, cost, days_rem, risk) in enumerate(raw_products):
            if not db.query(Inventory).filter(Inventory.product_code == sku).first():
                stock = random.randint(200, 2500) if risk != "HIGH" else random.randint(100, 400)
                demand = stock + random.randint(300, 800) if risk == "HIGH" else max(100, stock - random.randint(200, 500))
                prog = int((stock / max(demand, 1)) * 100)
                action_text = "Reorder immediately" if risk == "HIGH" else ("Reduce next purchase" if risk == "OVERSTOCK" else "Optimal level")
                
                db.add(Inventory(
                    product_code=sku,
                    name=name,
                    category=cat_name,
                    current_stock=stock,
                    forecast_demand=demand,
                    days_remaining=days_rem,
                    progress=min(100, max(5, prog)),
                    risk=risk,
                    action=action_text,
                    warehouse=warehouses[idx % len(warehouses)],
                    unit_cost=f"₹{cost}",
                    product_id=prod_map[sku].id
                ))
        db.commit()

        # 7. Sales History (90 Days for each product)
        print("Generating 90 days of Sales History data...")
        if db.query(SalesHistory).count() < 100:
            now = datetime.now(timezone.utc)
            history_rows = []
            for sku, prod_obj in prod_map.items():
                base_qty = random.randint(20, 150)
                cost_num = float(prod_obj.unit_cost.replace('₹', '').replace(',', ''))
                for day_idx in range(90, 0, -1):
                    dt = now - timedelta(days=day_idx)
                    qty = max(5, int(base_qty + random.uniform(-15, 25)))
                    rev = round(qty * cost_num * 1.25, 2)
                    history_rows.append(SalesHistory(
                        product_id=prod_obj.id,
                        timestamp=dt,
                        quantity=qty,
                        revenue=rev
                    ))
            db.bulk_save_objects(history_rows)
            db.commit()

        # 8. Demand Forecast Records
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
            db.commit()

        # 9. Fleet Routes & Deliveries
        if db.query(Route).count() == 0:
            routes_data = [
                Route(route_code="RT-8841", truck_id="MH-04-JK-4821", driver="Rajesh Kumar", origin="Mumbai Central Port", destination="Pune Logistics Hub", status="IN_TRANSIT", eta="14:35 (On Time)", temp="3.2°C", fuel_saved="₹1,850", risk="LOW"),
                Route(route_code="RT-9204", truck_id="MH-12-PQ-9102", driver="Suresh Patil", origin="Nashik Warehouse", destination="Thane Cold Storage", status="DELAYED", eta="16:20 (+25m NH-48 Traffic)", temp="4.1°C", fuel_saved="₹920", risk="MEDIUM"),
                Route(route_code="RT-7712", truck_id="MH-46-AB-3301", driver="Amit Shinde", origin="Pune North Hub", destination="Solapur Distribution", status="IN_TRANSIT", eta="18:00 (On Time)", temp="2.8°C", fuel_saved="₹2,400", risk="OPTIMAL"),
                Route(route_code="RT-6019", truck_id="MH-02-CD-5541", driver="Vikram Singh", origin="Surat Port Depot", destination="Mumbai Central", status="REROUTED", eta="15:10 (Auto-adjusted)", temp="3.5°C", fuel_saved="₹3,100", risk="AI_REROUTED")
            ]
            db.add_all(routes_data)
            db.commit()

            r_first = db.query(Route).first()
            db.add(Delivery(
                route_id=r_first.id if r_first else None,
                tracking_number="TRK-90021-IN",
                status="IN_TRANSIT",
                eta=datetime.now(timezone.utc) + timedelta(hours=3)
            ))
            db.commit()

        # 10. Wastage Records
        if db.query(Wastage).count() == 0:
            wastage_items = [
                Wastage(item_code="WS-401", product="Fresh Milk 1L", batch="B-884-21", quantity="120 L", reason="Cold chain temp spike (4.8°C)", loss_amount="₹6,480", severity="HIGH", agent_intervention="Temp adjusted remotely by Wastage Agent"),
                Wastage(item_code="WS-402", product="Organic Strawberries", batch="B-912-04", quantity="45 kg", reason="Shelf-life expiry near", loss_amount="₹13,500", severity="MEDIUM", agent_intervention="15% dynamic promo auto-applied"),
                Wastage(item_code="WS-403", product="Greek Yogurt 200g", batch="B-771-09", quantity="80 units", reason="Packaging seal breach", loss_amount="₹5,200", severity="LOW", agent_intervention="Supplier quality claim opened")
            ]
            db.add_all(wastage_items)
            db.commit()

        # 11. Notifications
        if db.query(Notification).count() == 0:
            notifications = [
                Notification(title="Stockout Risk Alert", message="Fresh Milk 1L in Mumbai Central is below safety threshold (8 days remaining).", type="WARNING"),
                Notification(title="Route Rerouted", message="Truck MH-02-CD-5541 automatically rerouted to bypass NH-48 congestion.", type="INFO"),
                Notification(title="Thermal Variance Resolved", message="Truck MH-12-PQ-9102 refrigeration remotely restored to 3.0°C.", type="SUCCESS")
            ]
            db.add_all(notifications)
            db.commit()

        # 12. Automation Logs
        if db.query(AutomationLog).count() == 0:
            rules = [
                AutomationLog(rule_code="AUT-101", name="Automated Stockout Reorder", trigger="Stock < 10 days of forecast demand", action="Generate Purchase Intent & Notify Operations Lead", status="ENABLED", executions_today=14),
                AutomationLog(rule_code="AUT-102", name="Cold Chain Thermal Guardrail", trigger="Truck Temp variance > 1.5°C for 10 minutes", action="Send remote HVAC override command + alert driver", status="ENABLED", executions_today=3),
                AutomationLog(rule_code="AUT-103", name="Dynamic Markdown for Near-Expiry", trigger="Perishable item expiry <= 5 days & stock > 50 units", action="Apply 15% discount on POS & E-commerce channels", status="ENABLED", executions_today=8),
                AutomationLog(rule_code="AUT-104", name="Congestion Reroute Trigger", trigger="Route delay estimate > 20 minutes", action="Auto-calculate alternate highway route & update GPS telemetry", status="ENABLED", executions_today=12)
            ]
            db.add_all(rules)
            db.commit()

        # 13. Agent Activity
        if db.query(AgentActivity).count() == 0:
            activities = [
                AgentActivity(agent_code="AG-01", agent="Forecast Agent", role="Predictive Analytics & Seasonal Spikes", status="ACTIVE", confidence="94%", tasks_processed=14280, latency="14ms", action="updated regional demand models for Q4.", details="Successfully adjusted for seasonal Diwali spikes in Northern regions.", time_ago="2m ago", color="primary"),
                AgentActivity(agent_code="AG-02", agent="Inventory Agent", role="Stockout Guard & Safety Stock Optimizer", status="ACTIVE", confidence="96%", tasks_processed=28910, latency="8ms", action="flagged stockout risk for 3 SKUs.", details="Affected warehouses: Mumbai Central, Pune North.", time_ago="14m ago", color="tertiary"),
                AgentActivity(agent_code="AG-03", agent="Wastage Agent", role="Perishable Monitoring & Dynamic Discounting", status="ACTIVE", confidence="91%", tasks_processed=9450, latency="22ms", action="optimized cold chain transit temps.", details="Detected 2°C variance in Truck ID: TS-442; corrected remotely.", time_ago="45m ago", color="secondary"),
                AgentActivity(agent_code="AG-04", agent="Route Agent", role="Traffic Rerouting & Fuel Economy", status="ACTIVE", confidence="98%", tasks_processed=18200, latency="11ms", action="rerouted 12 shipments due to NH-48 closure.", details="Estimated ETA delay: 15 mins. Saved ₹24k in fuel costs.", time_ago="1h ago", color="primary-container")
            ]
            db.add_all(activities)
            db.commit()

        # 14. Reports
        if db.query(Report).count() == 0:
            reports = [
                Report(report_code="REP-01", title="Q4 Supply Chain Efficiency & Cost Savings", date="Oct 24, 2024", type="Executive Summary", author="Copilot AI & Daksh Mehta", size="2.4 MB"),
                Report(report_code="REP-02", title="Perishable Wastage Audit & Thermal Telemetry", date="Oct 20, 2024", type="Operations Report", author="Wastage Prevention Agent", size="1.8 MB"),
                Report(report_code="REP-03", title="Regional Warehouse Capacity & Stockout Risk", date="Oct 15, 2024", type="Inventory Intelligence", author="Inventory Agent", size="4.1 MB")
            ]
            db.add_all(reports)
            db.commit()

        print("Database Seeding Completed Successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
