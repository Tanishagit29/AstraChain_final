from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="OPERATIONS_LEAD")
    is_active = Column(Boolean, default=True)


class Category(BaseModel):
    __tablename__ = "categories"

    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    products = relationship("Product", back_populates="category_rel")


class Product(BaseModel):
    __tablename__ = "products"

    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category_name = Column(String(100), nullable=False, default="General")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    unit_cost = Column(String(50), nullable=False, default="₹100")
    days_remaining = Column(Integer, default=10)
    risk_level = Column(String(50), default="HEALTHY")
    expiry_date = Column(DateTime, nullable=True)

    category_rel = relationship("Category", back_populates="products")
    inventory_items = relationship("Inventory", back_populates="product_rel")
    sales_history = relationship("SalesHistory", back_populates="product_rel")
    forecasts = relationship("Forecast", back_populates="product_rel")


class Inventory(BaseModel):
    __tablename__ = "inventory"

    product_code = Column(String(100), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    current_stock = Column(Integer, default=0)
    forecast_demand = Column(Integer, default=0)
    days_remaining = Column(Integer, default=0)
    progress = Column(Integer, default=50)
    risk = Column(String(50), default="HEALTHY")
    action = Column(String(255), nullable=True)
    warehouse = Column(String(255), default="Mumbai Central")
    unit_cost = Column(String(50), default="₹100")

    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_rel = relationship("Product", back_populates="inventory_items")


class SalesHistory(BaseModel):
    __tablename__ = "sales_history"

    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    quantity = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)

    product_rel = relationship("Product", back_populates="sales_history")


class Forecast(BaseModel):
    __tablename__ = "forecasts"

    day = Column(String(50), nullable=False)
    historical = Column(Integer, nullable=True)
    forecast = Column(Integer, nullable=False)
    confidence_upper = Column(Integer, nullable=False)
    confidence_lower = Column(Integer, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)

    product_rel = relationship("Product", back_populates="forecasts")


class Supplier(BaseModel):
    __tablename__ = "suppliers"

    supplier_code = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    reliability_score = Column(String(50), default="90%")
    on_time_delivery = Column(String(50), default="90%")
    lead_time_avg = Column(String(50), default="1.5 days")
    risk_level = Column(String(50), default="LOW")
    status = Column(String(50), default="VERIFIED")

    performances = relationship("SupplierPerformance", back_populates="supplier_rel")


class SupplierPerformance(BaseModel):
    __tablename__ = "supplier_performance"

    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    evaluation_date = Column(DateTime, default=datetime.utcnow)
    score = Column(Float, default=90.0)
    notes = Column(Text, nullable=True)

    supplier_rel = relationship("Supplier", back_populates="performances")


class Warehouse(BaseModel):
    __tablename__ = "warehouses"

    name = Column(String(255), unique=True, nullable=False)
    location = Column(String(255), nullable=False)
    capacity_sqft = Column(Integer, default=50000)


class Route(BaseModel):
    __tablename__ = "routes"

    route_code = Column(String(100), unique=True, index=True, nullable=False)
    truck_id = Column(String(100), nullable=False)
    driver = Column(String(255), nullable=False)
    origin = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    status = Column(String(50), default="IN_TRANSIT")
    eta = Column(String(100), nullable=False)
    temp = Column(String(50), default="3.0°C")
    fuel_saved = Column(String(50), default="₹1,000")
    risk = Column(String(50), default="LOW")

    deliveries = relationship("Delivery", back_populates="route_rel")


class RouteOptimizationPlan(BaseModel):
    """Persisted history of multi-stop route optimization runs (TSP-style VRP)."""
    __tablename__ = "route_optimization_plans"

    truck_id = Column(String(100), nullable=False)
    origin = Column(String(255), nullable=False)
    stops = Column(JSON, nullable=False, default=list)
    optimized_sequence = Column(JSON, nullable=False, default=list)
    algorithm = Column(String(100), default="Nearest Neighbor + 2-Opt")
    total_distance_km = Column(Float, default=0.0)
    naive_distance_km = Column(Float, default=0.0)
    total_duration_minutes = Column(Integer, default=0)
    fuel_cost_inr = Column(Float, default=0.0)
    fuel_saved_inr = Column(Float, default=0.0)
    savings_pct = Column(Float, default=0.0)


class Delivery(BaseModel):
    __tablename__ = "deliveries"

    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    tracking_number = Column(String(100), unique=True, nullable=False)
    status = Column(String(50), default="PENDING")
    eta = Column(DateTime, nullable=True)

    route_rel = relationship("Route", back_populates="deliveries")


class Wastage(BaseModel):
    __tablename__ = "wastage"

    item_code = Column(String(100), unique=True, index=True, nullable=False)
    product = Column(String(255), nullable=False)
    batch = Column(String(100), nullable=False)
    quantity = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    loss_amount = Column(String(100), nullable=False)
    severity = Column(String(50), default="MEDIUM")
    agent_intervention = Column(Text, nullable=True)


class Notification(BaseModel):
    __tablename__ = "notifications"

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="INFO")
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class AutomationLog(BaseModel):
    __tablename__ = "automation_logs"

    rule_code = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    trigger = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    status = Column(String(50), default="ENABLED")
    executions_today = Column(Integer, default=0)


class AgentActivity(BaseModel):
    __tablename__ = "agent_activity"

    agent_code = Column(String(100), unique=True, index=True, nullable=False)
    agent = Column(String(255), nullable=False)
    role = Column(String(255), nullable=True)
    status = Column(String(50), default="ACTIVE")
    confidence = Column(String(50), default="95%")
    tasks_processed = Column(Integer, default=0)
    latency = Column(String(50), default="10ms")
    action = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    time_ago = Column(String(100), default="Just now")
    color = Column(String(50), default="primary")


class Report(BaseModel):
    __tablename__ = "reports"

    report_code = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    date = Column(String(100), nullable=False)
    type = Column(String(100), nullable=False)
    author = Column(String(255), nullable=False)
    size = Column(String(50), default="1.0 MB")
