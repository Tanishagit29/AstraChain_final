import uuid
import asyncio
import socket
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.session import get_db
from app.models.all_models import Notification, AutomationLog, Inventory, Wastage
from app.services.pipeline_state import pipeline_state
from app.services.inventory_service import InventoryService
from app.services.rio_mart_intelligence import discount_pct_for_days
from app.core.logging import logger

router = APIRouter(prefix="/notifications", tags=["Manager Notification Hub"])

# Read, action and simulation tracking
READ_NOTIF_IDS: set = set()
RESTOCKED_PRODUCT_IDS: set = set()
MITIGATED_WASTAGE_IDS: set = set()
PRESTOCKED_FESTIVAL_IDS: set = set()
DISMISSED_NOTIF_IDS: set = set()
SIMULATED_NOTIFICATIONS: List[Dict[str, Any]] = []


# =============================================================================
# WebSocket Real-Time Connection Manager
# =============================================================================
class NotificationConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending message to WebSocket client: {e}")
                dead_connections.append(connection)
        for dead in dead_connections:
            if dead in self.active_connections:
                self.active_connections.remove(dead)


manager = NotificationConnectionManager()


# =============================================================================
# Mobile Phone Push & Remote Notification Dispatcher
# =============================================================================
def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "192.168.29.124"


LOCAL_IP = get_local_ip()

PHONE_PUSH_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "ntfy_topic": "astrachain-daksh-alert",
    "ntfy_server": "https://ntfy.sh",
    "telegram_enabled": False,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "notify_stockout": True,
    "notify_restock": True,
    "notify_wastage": True,
    "notify_festival": True,
}


async def dispatch_phone_push(title: str, message: str, alert_type: str, product_id: Optional[str] = None, suggested_qty: Optional[int] = None):
    """
    Sends real-time native push notifications directly to the manager's phone
    via NTFY (Android/iOS lock screen push) and optional Telegram bot.
    Includes 1-click action buttons on the phone notification!
    """
    if not PHONE_PUSH_CONFIG.get("enabled", True):
        return

    atype = (alert_type or "").upper()
    if "STOCKOUT" in atype and not PHONE_PUSH_CONFIG.get("notify_stockout", True):
        return
    if "RESTOCK" in atype and not PHONE_PUSH_CONFIG.get("notify_restock", True):
        return
    if "WASTAGE" in atype and not PHONE_PUSH_CONFIG.get("notify_wastage", True):
        return
    if "FESTIVAL" in atype and not PHONE_PUSH_CONFIG.get("notify_festival", True):
        return

    topic = PHONE_PUSH_CONFIG.get("ntfy_topic", "astrachain-daksh-alert").strip()
    server = PHONE_PUSH_CONFIG.get("ntfy_server", "https://ntfy.sh").rstrip("/")
    if not topic:
        return

    priority = "urgent" if "STOCKOUT" in atype or "WASTAGE" in atype else ("high" if "FESTIVAL" in atype else "default")
    tags = "warning,rotating_light" if "STOCKOUT" in atype else ("package,white_check_mark" if "RESTOCK" in atype else ("apple,warning" if "WASTAGE" in atype else "party_popper,sparkles"))

    headers = {
        "Title": title,
        "Priority": priority,
        "Tags": tags,
    }

    # Action buttons right on phone notification
    app_url = f"http://{LOCAL_IP}:5173"
    actions = [f"view, Open Dashboard, {app_url}"]
    if product_id and "STOCKOUT" in atype:
        actions.insert(0, f"view, 1-Click Restock, {app_url}/inventory")
    elif product_id and "WASTAGE" in atype:
        actions.insert(0, f"view, 1-Click Markdown, {app_url}/wastage")
    elif product_id and "FESTIVAL" in atype:
        actions.insert(0, f"view, 1-Click Pre-Stock, {app_url}/forecast")

    headers["Actions"] = "; ".join(actions)

    # 1. NTFY Instant Push to Phone
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            await client.post(f"{server}/{topic}", headers=headers, content=message.encode("utf-8"))
    except Exception as e:
        logger.warning(f"NTFY phone push delivery notice: {e}")

    # 2. Telegram Bot Dispatch (if configured)
    if (
        PHONE_PUSH_CONFIG.get("telegram_enabled")
        and PHONE_PUSH_CONFIG.get("telegram_bot_token")
        and PHONE_PUSH_CONFIG.get("telegram_chat_id")
    ):
        try:
            tg_token = PHONE_PUSH_CONFIG["telegram_bot_token"].strip()
            tg_chat = PHONE_PUSH_CONFIG["telegram_chat_id"].strip()
            tg_text = f"*{title}*\n\n{message}\n\n📱 [Open AstraChain on Mobile]({app_url})"
            async with httpx.AsyncClient(timeout=4.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    json={"chat_id": tg_chat, "text": tg_text, "parse_mode": "Markdown"}
                )
        except Exception as e:
            logger.warning(f"Telegram mobile push notice: {e}")


async def broadcast_live_event(event_type: str, notification: Dict[str, Any], extra: Optional[Dict[str, Any]] = None):
    """Broadcast an alert event to all connected live WebSocket clients and to phone."""
    payload = {
        "event": event_type,
        "notification": notification,
        "extra": extra or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await manager.broadcast(payload)

    # Dispatch to phone in background
    if notification:
        try:
            title = notification.get("title") or "AstraChain Alert"
            msg = notification.get("message") or ""
            ntype = notification.get("type") or event_type
            pid = notification.get("product_id")
            qty = notification.get("suggested_qty") or notification.get("quantity_added")
            await dispatch_phone_push(title, msg, ntype, pid, qty)
        except Exception as err:
            logger.warning(f"Background phone push skipped: {err}")


# =============================================================================
# Pydantic Request Models
# =============================================================================
class RestockRequest(BaseModel):
    product_id: str
    quantity: Optional[int] = 500
    notification_id: Optional[str] = None


class WastageMitigateRequest(BaseModel):
    product_id: str
    wastage_id: Optional[str] = None
    discount: Optional[str] = "30% Dynamic Markdown"
    notification_id: Optional[str] = None


class FestivalPrestockRequest(BaseModel):
    product_id: str
    festival_name: Optional[str] = "Diwali"
    quantity: Optional[int] = 500
    notification_id: Optional[str] = None


class SimulateAlertRequest(BaseModel):
    type: str = "stockout"  # stockout, restock, wastage, festival, random
    product_name: Optional[str] = None
    product_id: Optional[str] = None
    festival_name: Optional[str] = None
    quantity: Optional[int] = None
    days_remaining: Optional[int] = None


class PhoneConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    ntfy_topic: Optional[str] = None
    ntfy_server: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    notify_stockout: Optional[bool] = None
    notify_restock: Optional[bool] = None
    notify_wastage: Optional[bool] = None
    notify_festival: Optional[bool] = None


class TestPhonePushRequest(BaseModel):
    type: Optional[str] = "stockout"


# =============================================================================
# Mobile Phone Push Integration Endpoints
# =============================================================================
@router.get("/phone/config")
def get_phone_notification_config() -> Dict[str, Any]:
    """Returns mobile phone push settings, local Wi-Fi IP, and direct links."""
    topic = PHONE_PUSH_CONFIG.get("ntfy_topic", "astrachain-daksh-alert")
    server = PHONE_PUSH_CONFIG.get("ntfy_server", "https://ntfy.sh").rstrip("/")
    return {
        "success": True,
        "config": PHONE_PUSH_CONFIG,
        "local_ip": LOCAL_IP,
        "mobile_web_url": f"http://{LOCAL_IP}:5173",
        "ntfy_topic_url": f"{server}/{topic}",
        "ntfy_app_download": {
            "android": "https://play.google.com/store/apps/details?id=io.heckel.ntfy",
            "ios": "https://apps.apple.com/app/ntfy/id1625396347"
        }
    }


@router.post("/phone/config")
def update_phone_notification_config(payload: PhoneConfigUpdate) -> Dict[str, Any]:
    """Updates manager's phone notification channel preferences."""
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            PHONE_PUSH_CONFIG[k] = v
    topic = PHONE_PUSH_CONFIG.get("ntfy_topic", "astrachain-daksh-alert")
    server = PHONE_PUSH_CONFIG.get("ntfy_server", "https://ntfy.sh").rstrip("/")
    return {
        "success": True,
        "message": "Phone notification configuration updated successfully.",
        "config": PHONE_PUSH_CONFIG,
        "ntfy_topic_url": f"{server}/{topic}"
    }


@router.post("/phone/test")
async def send_test_phone_notification(payload: TestPhonePushRequest) -> Dict[str, Any]:
    """Sends an immediate test push notification directly to the manager's phone."""
    atype = (payload.type or "stockout").lower()
    if atype == "stockout":
        title = "🚨 Test Alert: Stockout Deficit"
        msg = "Amul Taaza Milk stock depleted to 0 units vs demand 1,200 at Mumbai Hub. 1-Click Replenishment ready on phone."
        pid = "SKU-MILK-101"
    elif atype == "wastage":
        title = "⚠️ Test Alert: Perishable Expiry"
        msg = "Fresh Paneer 200g expiring in 2 days at Cold Hub. 50% Dynamic Markdown authorized."
        pid = "SKU-PNR-515"
    elif atype == "festival":
        title = "🎪 Test Alert: Festive Surge"
        msg = "Diwali demand surge predicted: 2.8x uplift for Basmati Rice. Buffer recommendation ready on phone."
        pid = "SKU-RICE-501"
    else:
        title = "📦 Test Alert: Restocking Fulfilled"
        msg = "+500 units replenishment checked into warehouse dock. Status: Optimal Stock."
        pid = "SKU-GEN-01"

    await dispatch_phone_push(title, msg, atype.upper(), pid, 500)

    # Also broadcast locally via WebSocket
    test_notif = {
        "id": f"test-phone-{uuid.uuid4().hex[:6]}",
        "title": title,
        "message": msg,
        "type": atype.upper(),
        "severity": "CRITICAL" if atype == "stockout" else "SUCCESS",
        "product_id": pid,
        "product_name": "Test Item",
        "timestamp": "Just now",
        "badge": "Phone Alert Dispatched",
        "is_read": False
    }
    await manager.broadcast({"event": f"{atype.upper()}_ALERT", "notification": test_notif, "timestamp": datetime.now(timezone.utc).isoformat()})

    topic = PHONE_PUSH_CONFIG.get("ntfy_topic", "astrachain-daksh-alert")
    server = PHONE_PUSH_CONFIG.get("ntfy_server", "https://ntfy.sh").rstrip("/")
    return {
        "success": True,
        "message": f"Test push alert sent to phone via NTFY ({topic})",
        "topic": topic,
        "ntfy_url": f"{server}/{topic}"
    }


# =============================================================================
# WebSocket Endpoint for Live Real-Time Notifications
# =============================================================================
@router.websocket("/ws")
async def websocket_notifications_hub(websocket: WebSocket):
    """
    WebSocket endpoint for instant live push notifications.
    Streams stockout alerts, restock updates, perishable wastage warnings,
    and festival-wise restocking surge recommendations in real-time.
    """
    await manager.connect(websocket)
    try:
        # Send initial connection handshake
        await websocket.send_json({
            "event": "CONNECTED",
            "message": "Connected to AstraChain Live Notification Stream",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channel": "manager-operations"
        })

        while True:
            # Keep connection open, handle client heartbeats
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "PONG", "timestamp": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket handler exited: {e}")
        manager.disconnect(websocket)


# =============================================================================
# Manager Notification Feed
# =============================================================================
@router.get("")
def get_manager_notifications(
    db: Session = Depends(get_db),
    unread_only: bool = False
) -> Dict[str, Any]:
    """
    Returns active operational notifications for the manager:
    1. Real-time stockout risk alerts with 1-Click Restock.
    2. Restocked items and restocking fulfillment updates.
    3. Perishable wastage & near-expiry alerts with 1-Click Dynamic Markdown.
    4. Festival-wise demand surge restocking recommendations with 1-Click Pre-Stock.
    5. Persisted audit trail and supply chain telemetry logs.
    """
    # Ensure default pipeline views are available if not yet initialized
    if not pipeline_state.inventory_analysis:
        try:
            pipeline_state.load_default_near_expiry_items()
        except Exception as e:
            logger.warning(f"Default pipeline items lazy load skipped: {e}")

    notifications: List[Dict[str, Any]] = []
    seen_products = set()

    # =========================================================================
    # 1. Real-time Stockout Notifications (Pipeline + DB Inventory)
    # =========================================================================
    for item in pipeline_state.inventory_analysis:
        pid = item.get("product_id") or ""
        pname = item.get("product_name") or "Unknown Product"
        stat = item.get("status")

        if pid in seen_products:
            continue

        if stat in ["Stockout Risk", "Low Stock"]:
            seen_products.add(pid)
            notif_id = f"stockout-{pid}"
            if notif_id in DISMISSED_NOTIF_IDS:
                continue

            is_read = notif_id in READ_NOTIF_IDS
            is_restocked = pid in RESTOCKED_PRODUCT_IDS or item.get("is_restocked", False)

            curr_stock = item.get("current_stock", 0)
            demand = item.get("predicted_demand", 0)
            suggested = item.get("suggested_reorder_qty") or 500

            notifications.append({
                "id": notif_id,
                "title": f"Stockout Alert: {pname}",
                "message": (
                    f"Critical stock deficit at {item.get('warehouse', 'Logistics Hub')}. "
                    f"Current stock: {curr_stock:,} units vs Predicted Demand: {demand:,} units. "
                    f"Immediate replenishment authorized."
                ),
                "type": "STOCKOUT",
                "severity": "CRITICAL" if stat == "Stockout Risk" else "WARNING",
                "product_id": pid,
                "product_name": pname,
                "current_stock": curr_stock,
                "predicted_demand": demand,
                "suggested_qty": suggested,
                "warehouse": item.get("warehouse", "Logistics Hub"),
                "can_restock": not is_restocked,
                "is_restocked": is_restocked,
                "is_read": is_read,
                "timestamp": "Real-time Alert",
                "badge": "1-Click Restock Ready" if not is_restocked else "Restocked"
            })

    # Also check database Inventory for high-risk stockouts
    try:
        db_stockouts = db.query(Inventory).filter(Inventory.risk.in_(["HIGH", "CRITICAL"])).all()
        for dbi in db_stockouts:
            if dbi.product_code in seen_products:
                continue
            seen_products.add(dbi.product_code)
            notif_id = f"stockout-db-{dbi.product_code}"
            if notif_id in DISMISSED_NOTIF_IDS:
                continue

            is_read = notif_id in READ_NOTIF_IDS
            is_restocked = dbi.product_code in RESTOCKED_PRODUCT_IDS

            notifications.append({
                "id": notif_id,
                "title": f"Stockout Alert: {dbi.name}",
                "message": f"Inventory running low in {dbi.warehouse}. {dbi.days_remaining} days remaining of safety stock. Single-click replenishment authorized.",
                "type": "STOCKOUT",
                "severity": "HIGH",
                "product_id": dbi.product_code,
                "product_name": dbi.name,
                "current_stock": dbi.current_stock,
                "predicted_demand": dbi.forecast_demand or 500,
                "suggested_qty": 500,
                "warehouse": dbi.warehouse,
                "can_restock": not is_restocked,
                "is_restocked": is_restocked,
                "is_read": is_read,
                "timestamp": "Active Risk",
                "badge": "1-Click Restock Ready" if not is_restocked else "Restocked"
            })
    except Exception as e:
        logger.warning(f"Error querying DB inventory for stockout notifications: {e}")

    # =========================================================================
    # 2. Perishable Wastage & Near-Expiry Alerts (Wastage Agent + DB)
    # =========================================================================
    seen_wastage_products = set()

    for item in pipeline_state.wastage_decisions:
        pid = item.get("product_id") or ""
        pname = item.get("product_name") or "Perishable Asset"
        days_rem = item.get("days_remaining")

        if pid in seen_wastage_products or days_rem is None:
            continue

        # Include items approaching expiry within 5 days
        if 0 <= days_rem <= 5:
            seen_wastage_products.add(pid)
            notif_id = f"wastage-{pid}"
            if notif_id in DISMISSED_NOTIF_IDS:
                continue

            is_mitigated = pid in MITIGATED_WASTAGE_IDS or notif_id in MITIGATED_WASTAGE_IDS
            is_read = notif_id in READ_NOTIF_IDS
            stk = item.get("current_stock", 80)
            wh = item.get("warehouse", "Main Cold Storage")
            disc = item.get("discount") or f"{discount_pct_for_days(days_rem)}% Dynamic Promo Markdown"

            notifications.append({
                "id": notif_id,
                "title": f"Wastage Alert: {pname}",
                "message": (
                    f"Shelf-life alert: {stk} units approaching expiry ({days_rem} day{'s' if days_rem != 1 else ''} left) at {wh}. "
                    f"Dynamic markdown recommendation: {disc} for prompt volume clearance."
                ),
                "type": "WASTAGE",
                "severity": "CRITICAL" if days_rem <= 2 else "WARNING",
                "product_id": pid,
                "product_name": pname,
                "current_stock": stk,
                "days_remaining": days_rem,
                "discount_recommended": disc,
                "warehouse": wh,
                "can_mitigate": not is_mitigated,
                "is_mitigated": is_mitigated,
                "is_read": is_read,
                "timestamp": f"{days_rem}d to Expiry",
                "badge": "1-Click Markdown" if not is_mitigated else "Markdown Active"
            })

    # Also check DB Wastage items if pipeline has fewer items
    try:
        db_wastage = db.query(Wastage).filter(Wastage.severity.in_(["HIGH", "MEDIUM"])).limit(3).all()
        for dw in db_wastage:
            if dw.item_code in seen_wastage_products or dw.product in seen_wastage_products:
                continue
            seen_wastage_products.add(dw.item_code)
            notif_id = f"wastage-db-{dw.item_code}"
            if notif_id in DISMISSED_NOTIF_IDS:
                continue

            is_mitigated = dw.item_code in MITIGATED_WASTAGE_IDS or notif_id in MITIGATED_WASTAGE_IDS
            is_read = notif_id in READ_NOTIF_IDS

            notifications.append({
                "id": notif_id,
                "title": f"Wastage Alert: {dw.product}",
                "message": f"Wastage risk reported: {dw.quantity} units under batch {dw.batch}. {dw.reason}. Loss exposure: {dw.loss_amount}.",
                "type": "WASTAGE",
                "severity": "WARNING" if dw.severity == "MEDIUM" else "CRITICAL",
                "product_id": dw.item_code,
                "product_name": dw.product,
                "current_stock": dw.quantity,
                "days_remaining": 3,
                "discount_recommended": "30% Clearance Discount",
                "warehouse": "Central Facility",
                "can_mitigate": not is_mitigated,
                "is_mitigated": is_mitigated,
                "is_read": is_read,
                "timestamp": "Batch Risk",
                "badge": "Clearance Ready" if not is_mitigated else "Mitigated"
            })
    except Exception as e:
        logger.warning(f"Error querying DB wastage: {e}")

    # =========================================================================
    # 3. Festival-Wise Restocking Recommendations
    # =========================================================================
    try:
        from app.services.festival_service import FestivalForecastService
        fest_demand_resp = FestivalForecastService.get_festival_item_demand(db, festival_name=None, limit=5)
        target_fest_name = fest_demand_resp.festival_name or "Diwali"
        fest_items = getattr(fest_demand_resp, "items", None) or getattr(fest_demand_resp, "top_demand_items", [])

        for f_item in fest_items[:4]:
            notif_id = f"fest-rec-{f_item.product_id}"
            if notif_id in DISMISSED_NOTIF_IDS:
                continue

            is_prestocked = f_item.product_id in PRESTOCKED_FESTIVAL_IDS or notif_id in PRESTOCKED_FESTIVAL_IDS
            is_read = notif_id in READ_NOTIF_IDS
            suggested_buffer = max(getattr(f_item, "extra_units_needed", getattr(f_item, "extra_inventory_needed", 600)), 600)

            notifications.append({
                "id": notif_id,
                "title": f"Festival Restock Rec: {f_item.product_name}",
                "message": (
                    f"Anticipated {f_item.festival_multiplier}x demand surge (+{f_item.uplift_pct}%) for upcoming {target_fest_name}. "
                    f"Projected sales: {f_item.festival_period_sales:,} units vs current stock: {f_item.current_stock:,} units. "
                    f"Recommended festival buffer: +{suggested_buffer:,} units."
                ),
                "type": "FESTIVAL",
                "severity": "PROMO",
                "festival_name": target_fest_name,
                "product_id": f_item.product_id,
                "product_name": f_item.product_name,
                "current_stock": f_item.current_stock,
                "predicted_demand": f_item.festival_period_sales,
                "suggested_qty": suggested_buffer,
                "festival_multiplier": f_item.festival_multiplier,
                "uplift_pct": f_item.uplift_pct,
                "can_prestock": not is_prestocked,
                "is_prestocked": is_prestocked,
                "is_read": is_read,
                "timestamp": f"{target_fest_name} Window",
                "badge": "1-Click Pre-Stock" if not is_prestocked else "Buffer Stocked"
            })
    except Exception as e:
        logger.warning(f"Error fetching festival restocking recommendations: {e}")

    # =========================================================================
    # 4. Simulated / Dynamically Injected Notifications
    # =========================================================================
    for sim_n in reversed(SIMULATED_NOTIFICATIONS):
        if sim_n["id"] not in DISMISSED_NOTIF_IDS:
            sim_copy = dict(sim_n)
            sim_copy["is_read"] = sim_copy["id"] in READ_NOTIF_IDS
            if sim_copy.get("product_id") in RESTOCKED_PRODUCT_IDS:
                sim_copy["is_restocked"] = True
                sim_copy["can_restock"] = False
                sim_copy["badge"] = "Restocked"
            if sim_copy.get("product_id") in MITIGATED_WASTAGE_IDS:
                sim_copy["is_mitigated"] = True
                sim_copy["can_mitigate"] = False
                sim_copy["badge"] = "Markdown Active"
            if sim_copy.get("product_id") in PRESTOCKED_FESTIVAL_IDS:
                sim_copy["is_prestocked"] = True
                sim_copy["can_prestock"] = False
                sim_copy["badge"] = "Buffer Stocked"
            notifications.insert(0, sim_copy)

    # =========================================================================
    # 5. Persisted Restock & System Notifications from DB
    # =========================================================================
    try:
        db_notifs = db.query(Notification).order_by(Notification.id.desc()).limit(20).all()
        for dn in db_notifs:
            notif_id = f"db-{dn.id}"
            if notif_id in DISMISSED_NOTIF_IDS:
                continue

            ts_str = dn.timestamp.strftime("%b %d, %H:%M") if dn.timestamp else "Recently"
            is_success = dn.type == "SUCCESS"
            is_restock_type = "Restocked" in dn.title or "Stockout Restocked" in dn.title

            notifications.append({
                "id": notif_id,
                "title": dn.title,
                "message": dn.message,
                "type": "RESTOCKED" if is_restock_type else (dn.type or "INFO"),
                "severity": "SUCCESS" if is_success else ("WARNING" if dn.type == "WARNING" else "INFO"),
                "product_id": None,
                "product_name": None,
                "can_restock": False,
                "is_restocked": True if is_restock_type else False,
                "is_read": dn.is_read or (notif_id in READ_NOTIF_IDS),
                "timestamp": ts_str,
                "badge": "Resolved" if is_success else "Telemetry"
            })
    except Exception as e:
        logger.warning(f"Error fetching DB notifications: {e}")

    # Calculate categorized counts
    stockout_count = sum(1 for n in notifications if n["type"] == "STOCKOUT" and not n.get("is_restocked"))
    wastage_count = sum(1 for n in notifications if n["type"] == "WASTAGE" and not n.get("is_mitigated"))
    festival_count = sum(1 for n in notifications if n["type"] == "FESTIVAL" and not n.get("is_prestocked"))
    restocked_count = sum(1 for n in notifications if n["type"] == "RESTOCKED" or n.get("is_restocked"))
    unread_count = sum(1 for n in notifications if not n["is_read"])

    if unread_only:
        notifications = [n for n in notifications if not n["is_read"]]

    return {
        "success": True,
        "unread_count": unread_count,
        "stockout_count": stockout_count,
        "wastage_count": wastage_count,
        "festival_count": festival_count,
        "restocked_count": restocked_count,
        "total": len(notifications),
        "data": notifications
    }


# =============================================================================
# 1-Click Action Handlers (with Live WebSocket Broadcasts)
# =============================================================================
@router.post("/restock")
async def restock_stockout_product(
    payload: RestockRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Executes single-click restocking for a stockout product.
    Immediately increments stock count, updates safety thresholds, marks the stockout
    as resolved, logs the manager authorization to the audit trail, and broadcasts
    the live restocking event to all connected UI clients.
    """
    qty = payload.quantity or 500
    target_id = payload.product_id

    # 1. Restock in Pipeline State
    pipe_item = pipeline_state.restock_item(target_id, qty)

    # 2. Restock in Database Inventory
    db_item = InventoryService.restock_item(db, target_id, qty)

    product_name = target_id
    if pipe_item:
        product_name = pipe_item.get("product_name", target_id)
    elif db_item:
        product_name = db_item.name

    new_stock = pipe_item.get("current_stock") if pipe_item else (db_item.current_stock if db_item else qty)

    # Track in restocked set
    RESTOCKED_PRODUCT_IDS.add(target_id)
    if payload.notification_id:
        READ_NOTIF_IDS.add(payload.notification_id)

    # Record Success Notification in DB
    try:
        success_notif = Notification(
            title=f"Stockout Restocked: {product_name}",
            message=f"Manager Daksh Mehta authorized 1-Click Restock (+{qty:,} units). Current stock level: {new_stock:,} units. Stockout risk cleared.",
            type="SUCCESS",
            is_read=False
        )
        db.add(success_notif)

        # Record Automation Audit Log
        rule_code = f"AUT-RESTOCK-{uuid.uuid4().hex[:8].upper()}"
        log_entry = AutomationLog(
            rule_code=rule_code,
            name=f"1-Click Stockout Replenishment: {product_name}",
            trigger=f"Stockout threshold breached for {target_id}",
            action=f"Manager Daksh Mehta single-click restocked {qty:,} units to warehouse",
            status="EXECUTED"
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record restock notification or audit log: {e}")

    logger.info(f"1-Click Restock executed for '{target_id}' (+{qty} units).")

    # Broadcast Live Restock Notification to all connected clients
    live_notif = {
        "id": f"restock-{uuid.uuid4().hex[:8]}",
        "title": f"Restocked: {product_name}",
        "message": f"Manager Daksh Mehta replenished +{qty:,} units. Warehouse balance updated to {new_stock:,} units. Status: Optimal Stock.",
        "type": "RESTOCKED",
        "severity": "SUCCESS",
        "product_id": target_id,
        "product_name": product_name,
        "quantity_added": qty,
        "new_stock": new_stock,
        "timestamp": "Just now",
        "badge": "Restocked",
        "is_read": False,
        "is_restocked": True
    }
    await broadcast_live_event("RESTOCK_COMPLETED", live_notif, {"product_id": target_id, "quantity": qty, "new_stock": new_stock})

    return {
        "success": True,
        "message": f"Successfully restocked '{product_name}' with {qty:,} units! Stockout risk resolved.",
        "product_id": target_id,
        "product_name": product_name,
        "quantity_added": qty,
        "new_stock": new_stock,
        "status": "Optimal Stock"
    }


@router.post("/wastage/mitigate")
async def mitigate_wastage_alert(
    payload: WastageMitigateRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Executes single-click wastage prevention for a near-expiry product.
    Applies recommended promotional markdown, updates pipeline state,
    records success audit log, and broadcasts live alert mitigation event.
    """
    target_id = payload.product_id
    discount = payload.discount or "30% Dynamic Markdown"

    MITIGATED_WASTAGE_IDS.add(target_id)
    if payload.notification_id:
        MITIGATED_WASTAGE_IDS.add(payload.notification_id)
        READ_NOTIF_IDS.add(payload.notification_id)

    product_name = target_id
    # Find product name in pipeline wastage decisions
    for item in pipeline_state.wastage_decisions:
        if item.get("product_id") == target_id or item.get("product_name") == target_id:
            product_name = item.get("product_name", target_id)
            item["decision"] = "Apply Discount"
            item["discount"] = discount
            break

    # Record notification and audit log
    try:
        success_notif = Notification(
            title=f"Wastage Markdown Activated: {product_name}",
            message=f"Manager Daksh Mehta authorized {discount} to clear expiring stock rapidly and eliminate wastage loss.",
            type="SUCCESS",
            is_read=False
        )
        db.add(success_notif)

        rule_code = f"AUT-WASTAGE-{uuid.uuid4().hex[:8].upper()}"
        log_entry = AutomationLog(
            rule_code=rule_code,
            name=f"1-Click Wastage Mitigation: {product_name}",
            trigger=f"Near-expiry shelf life alert for {target_id}",
            action=f"Manager Daksh Mehta applied {discount} for immediate volume liquidation",
            status="EXECUTED"
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record wastage mitigation log: {e}")

    logger.info(f"1-Click Wastage mitigation authorized for '{target_id}' ({discount}).")

    # Broadcast Live Wastage Mitigated Notification
    live_notif = {
        "id": f"wastage-mitigated-{uuid.uuid4().hex[:8]}",
        "title": f"Markdown Active: {product_name}",
        "message": f"Dynamic promo discount ({discount}) is now active. Stock flagged for priority retail liquidation.",
        "type": "WASTAGE",
        "severity": "SUCCESS",
        "product_id": target_id,
        "product_name": product_name,
        "discount_applied": discount,
        "timestamp": "Just now",
        "badge": "Markdown Active",
        "is_read": False,
        "is_mitigated": True
    }
    await broadcast_live_event("WASTAGE_MITIGATED", live_notif, {"product_id": target_id, "discount": discount})

    return {
        "success": True,
        "message": f"Successfully activated {discount} for '{product_name}'! Volume clearance initiated.",
        "product_id": target_id,
        "product_name": product_name,
        "discount_applied": discount,
        "status": "Markdown Active"
    }


@router.post("/festival/prestock")
async def prestock_festival_recommendation(
    payload: FestivalPrestockRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Executes single-click pre-stocking for an upcoming festival demand surge.
    Replenishes buffer inventory in pipeline & database, logs the manager authorization,
    and broadcasts the live festive pre-stock fulfillment event.
    """
    target_id = payload.product_id
    fest_name = payload.festival_name or "Diwali"
    qty = payload.quantity or 600

    PRESTOCKED_FESTIVAL_IDS.add(target_id)
    if payload.notification_id:
        PRESTOCKED_FESTIVAL_IDS.add(payload.notification_id)
        READ_NOTIF_IDS.add(payload.notification_id)

    # 1. Restock in Pipeline State
    pipe_item = pipeline_state.restock_item(target_id, qty)

    # 2. Restock in Database Inventory
    db_item = InventoryService.restock_item(db, target_id, qty)

    product_name = target_id
    if pipe_item:
        product_name = pipe_item.get("product_name", target_id)
    elif db_item:
        product_name = db_item.name

    # Record notification and audit log
    try:
        success_notif = Notification(
            title=f"Festival Buffer Allocated: {product_name}",
            message=f"Manager Daksh Mehta authorized +{qty:,} units festival buffer for upcoming {fest_name} surge.",
            type="SUCCESS",
            is_read=False
        )
        db.add(success_notif)

        rule_code = f"AUT-FESTIVAL-{uuid.uuid4().hex[:8].upper()}"
        log_entry = AutomationLog(
            rule_code=rule_code,
            name=f"Festival Surge Pre-Stock: {product_name} ({fest_name})",
            trigger=f"Projected festive demand uplift during {fest_name}",
            action=f"Manager Daksh Mehta single-click allocated +{qty:,} units safety buffer",
            status="EXECUTED"
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record festival prestock log: {e}")

    logger.info(f"Festival prestock allocated for '{target_id}' (+{qty} units for {fest_name}).")

    # Broadcast Live Festival Prestocked Notification
    live_notif = {
        "id": f"fest-prestocked-{uuid.uuid4().hex[:8]}",
        "title": f"Buffer Stocked: {product_name}",
        "message": f"+{qty:,} units safety stock allocated for {fest_name} demand surge. Fulfillment ready.",
        "type": "FESTIVAL",
        "severity": "SUCCESS",
        "product_id": target_id,
        "product_name": product_name,
        "festival_name": fest_name,
        "quantity_added": qty,
        "timestamp": "Just now",
        "badge": "Buffer Stocked",
        "is_read": False,
        "is_prestocked": True
    }
    await broadcast_live_event("FESTIVAL_PRESTOCKED", live_notif, {"product_id": target_id, "festival": fest_name, "quantity": qty})

    return {
        "success": True,
        "message": f"Successfully pre-stocked +{qty:,} units for {fest_name} surge! Buffer allocated.",
        "product_id": target_id,
        "product_name": product_name,
        "festival_name": fest_name,
        "quantity_added": qty,
        "status": "Buffer Stocked"
    }


# =============================================================================
# Live Alert Simulation Engine (for testing & interactive demo)
# =============================================================================
@router.post("/simulate")
async def simulate_live_notification(
    payload: SimulateAlertRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Simulates a live notification event (Stockout, Restock, Wastage, or Festival)
    and pushes it instantly to all connected UI clients over WebSocket.
    """
    alert_type = payload.type.lower()
    notif_id = f"sim-{uuid.uuid4().hex[:8]}"
    generated_notif: Dict[str, Any] = {}

    if alert_type == "stockout":
        pid = payload.product_id or f"SKU-STK-{uuid.uuid4().hex[:4].upper()}"
        pname = payload.product_name or "Amul Pure Ghee 1L Tin"
        curr_stock = 8
        pred_demand = 620
        suggested = payload.quantity or 600

        generated_notif = {
            "id": notif_id,
            "title": f"Stockout Alert: {pname}",
            "message": f"Critical stockout risk: stock dropped to {curr_stock} units vs predicted demand {pred_demand} units at Central Warehouse. 1-Click replenishment authorized.",
            "type": "STOCKOUT",
            "severity": "CRITICAL",
            "product_id": pid,
            "product_name": pname,
            "current_stock": curr_stock,
            "predicted_demand": pred_demand,
            "suggested_qty": suggested,
            "warehouse": "Central Warehouse Hub",
            "can_restock": True,
            "is_restocked": False,
            "is_read": False,
            "timestamp": "Just now",
            "badge": "1-Click Restock Ready"
        }
        event_name = "STOCKOUT_ALERT"

    elif alert_type == "restock":
        pid = payload.product_id or f"SKU-RST-{uuid.uuid4().hex[:4].upper()}"
        pname = payload.product_name or "Tata Sampann Basmati Rice 5kg"
        qty = payload.quantity or 500
        new_stock = 580

        generated_notif = {
            "id": notif_id,
            "title": f"Restocked: {pname}",
            "message": f"Supplier replenishment confirmed: +{qty:,} units checked into warehouse dock. Inventory level healthy ({new_stock:,} units).",
            "type": "RESTOCKED",
            "severity": "SUCCESS",
            "product_id": pid,
            "product_name": pname,
            "quantity_added": qty,
            "new_stock": new_stock,
            "warehouse": "Logistics Hub 2",
            "can_restock": False,
            "is_restocked": True,
            "is_read": False,
            "timestamp": "Just now",
            "badge": "Restocked"
        }
        event_name = "RESTOCK_COMPLETED"

    elif alert_type == "wastage":
        pid = payload.product_id or f"SKU-WST-{uuid.uuid4().hex[:4].upper()}"
        pname = payload.product_name or "Fresh Malai Paneer 200g"
        days_rem = payload.days_remaining if payload.days_remaining is not None else 2
        stk = payload.quantity or 95
        disc = "50% Dynamic Promo Markdown" if days_rem <= 2 else "30% Dynamic Markdown"

        generated_notif = {
            "id": notif_id,
            "title": f"Wastage Alert: {pname}",
            "message": f"Perishable shelf-life warning: {stk} units approaching expiry in {days_rem} day{'s' if days_rem != 1 else ''} at Cold Facility. Recommended: {disc} for rapid inventory clearance.",
            "type": "WASTAGE",
            "severity": "CRITICAL" if days_rem <= 2 else "WARNING",
            "product_id": pid,
            "product_name": pname,
            "current_stock": stk,
            "days_remaining": days_rem,
            "discount_recommended": disc,
            "warehouse": "Main Cold Chain Hub",
            "can_mitigate": True,
            "is_mitigated": False,
            "is_read": False,
            "timestamp": f"{days_rem}d to Expiry",
            "badge": "1-Click Markdown"
        }
        event_name = "WASTAGE_ALERT"

    elif alert_type == "festival":
        fest = payload.festival_name or "Diwali"
        pid = payload.product_id or f"SKU-FEST-{uuid.uuid4().hex[:4].upper()}"
        pname = payload.product_name or "Haldiram's Soan Papdi 1kg Premium"
        mult = 2.8
        uplift = 180
        curr_stock = 150
        sales = 1100
        suggested = payload.quantity or 950

        generated_notif = {
            "id": notif_id,
            "title": f"Festival Restock Rec: {pname}",
            "message": f"Projected {mult}x demand surge (+{uplift}%) for upcoming {fest}. Projected sales: {sales:,} units vs current stock: {curr_stock:,} units. Recommended festival buffer: +{suggested:,} units.",
            "type": "FESTIVAL",
            "severity": "PROMO",
            "festival_name": fest,
            "product_id": pid,
            "product_name": pname,
            "current_stock": curr_stock,
            "predicted_demand": sales,
            "suggested_qty": suggested,
            "festival_multiplier": mult,
            "uplift_pct": uplift,
            "can_prestock": True,
            "is_prestocked": False,
            "is_read": False,
            "timestamp": f"{fest} Surge",
            "badge": "1-Click Pre-Stock"
        }
        event_name = "FESTIVAL_ALERT"

    else:
        # Default fallback to stockout
        pid = f"SKU-GEN-{uuid.uuid4().hex[:4].upper()}"
        pname = "Organic Whole Wheat Atta 10kg"
        generated_notif = {
            "id": notif_id,
            "title": f"Stockout Alert: {pname}",
            "message": f"Buffer depletion alert: Only 15 units remaining at Regional Depo. Immediate +500 unit reorder recommended.",
            "type": "STOCKOUT",
            "severity": "CRITICAL",
            "product_id": pid,
            "product_name": pname,
            "current_stock": 15,
            "predicted_demand": 500,
            "suggested_qty": 500,
            "warehouse": "Regional Depo",
            "can_restock": True,
            "is_restocked": False,
            "is_read": False,
            "timestamp": "Just now",
            "badge": "1-Click Restock Ready"
        }
        event_name = "STOCKOUT_ALERT"

    # Store in simulated array
    SIMULATED_NOTIFICATIONS.append(generated_notif)

    # Broadcast via WebSocket in real-time
    await broadcast_live_event(event_name, generated_notif)

    return {
        "success": True,
        "message": f"Live notification simulation broadcasted ({event_name})",
        "notification": generated_notif
    }


# =============================================================================
# Read and Dismissal Management
# =============================================================================
@router.post("/mark-all-read")
def mark_all_notifications_read(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Marks all operational notifications as read."""
    # Mark in-memory generated IDs
    for item in pipeline_state.inventory_analysis:
        pid = item.get("product_id")
        if pid:
            READ_NOTIF_IDS.add(f"stockout-{pid}")
            READ_NOTIF_IDS.add(f"stockout-db-{pid}")

    for item in pipeline_state.wastage_decisions:
        pid = item.get("product_id")
        if pid:
            READ_NOTIF_IDS.add(f"wastage-{pid}")
            READ_NOTIF_IDS.add(f"wastage-db-{pid}")

    for sim_n in SIMULATED_NOTIFICATIONS:
        READ_NOTIF_IDS.add(sim_n["id"])

    try:
        from app.services.festival_service import FestivalForecastService
        fest_demand_resp = FestivalForecastService.get_festival_item_demand(db, festival_name=None, limit=10)
        fest_items = getattr(fest_demand_resp, "items", None) or getattr(fest_demand_resp, "top_demand_items", [])
        for f_item in fest_items:
            READ_NOTIF_IDS.add(f"fest-rec-{f_item.product_id}")
            READ_NOTIF_IDS.add(f"festival-{f_item.product_id}")
    except Exception:
        pass

    try:
        for dbi in db.query(Inventory).all():
            READ_NOTIF_IDS.add(f"stockout-{dbi.product_code}")
            READ_NOTIF_IDS.add(f"stockout-db-{dbi.product_code}")
    except Exception:
        pass

    # Mark DB notifications as read
    try:
        db.query(Notification).update({Notification.is_read: True})
        db.commit()
    except Exception as e:
        logger.warning(f"Error marking DB notifications as read: {e}")

    return {
        "success": True,
        "message": "All notifications marked as read."
    }


@router.post("/{notification_id}/read")
def mark_single_notification_read(
    notification_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Marks a single notification as read."""
    READ_NOTIF_IDS.add(notification_id)

    if notification_id.startswith("db-"):
        try:
            raw_id = int(notification_id.replace("db-", ""))
            db_n = db.query(Notification).filter(Notification.id == raw_id).first()
            if db_n:
                db_n.is_read = True
                db.commit()
        except Exception as e:
            logger.warning(f"Error updating single DB notification: {e}")

    return {
        "success": True,
        "message": f"Notification '{notification_id}' marked as read."
    }


@router.delete("/{notification_id}")
def dismiss_notification(
    notification_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Dismisses/hides a notification from the manager's feed."""
    DISMISSED_NOTIF_IDS.add(notification_id)
    READ_NOTIF_IDS.add(notification_id)

    if notification_id.startswith("db-"):
        try:
            raw_id = int(notification_id.replace("db-", ""))
            db.query(Notification).filter(Notification.id == raw_id).delete()
            db.commit()
        except Exception as e:
            logger.warning(f"Error deleting DB notification: {e}")

    return {
        "success": True,
        "message": f"Notification '{notification_id}' dismissed."
    }
