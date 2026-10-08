import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services.inventory_service import InventoryService
from app.services.wastage_service import WastageService
from app.services.festival_service import FestivalForecastService
from app.services.pipeline_state import pipeline_state
from app.models.all_models import Notification, AutomationLog, AgentActivity

logger = logging.getLogger(__name__)


class AutonomousAgentScheduler:
    """
    Autonomous Background Agent Scheduler (Stage 5).
    Periodically runs background agent evaluations for:
    - Low-stock inventory risks & auto-reorders
    - Near-expiry perishable monitoring & dynamic markdowns
    - Upcoming festival demand surges
    Operates continuously without requiring manual user clicks.
    """

    def __init__(self, interval_seconds: int = 300):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.last_sweep_time: Optional[datetime] = None
        self.sweeps_completed = 0

    async def start(self):
        """Starts the background loop."""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._background_loop())
        logger.info(f"AutonomousAgentScheduler started with interval={self.interval_seconds}s")

    async def stop(self):
        """Stops the background loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AutonomousAgentScheduler stopped")

    async def _background_loop(self):
        while self.is_running:
            try:
                db = SessionLocal()
                try:
                    self.run_autonomous_sweep(db)
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Error in AutonomousAgentScheduler sweep loop: {e}")
            await asyncio.sleep(self.interval_seconds)

    def run_autonomous_sweep(self, db: Session) -> Dict[str, Any]:
        """
        Executes a complete autonomous sweep across low-stock, near-expiry, and upcoming festivals.
        """
        self.last_sweep_time = datetime.now(timezone.utc)
        self.sweeps_completed += 1

        actions_triggered = []
        reasoning = []

        # 1. Low stock sweep (Inventory Agent AG-02)
        try:
            low_stock_items = InventoryService.get_low_stock_items(db)
            if low_stock_items:
                reasoning.append(f"Detected {len(low_stock_items)} low-stock item(s).")
                for idx, item in enumerate(low_stock_items[:5]):
                    qty = getattr(item, "suggested_reorder_qty", 300) or 300
                    target_id = getattr(item, "product_code", "SKU-LOW-STOCK")
                    rule_code = f"AUT-REORDER-{target_id}-{idx+1}"

                    is_high_impact = qty > 500
                    status_str = "PENDING_APPROVAL" if is_high_impact else "EXECUTED"

                    log_entry = db.query(AutomationLog).filter(AutomationLog.rule_code == rule_code).first()
                    if not log_entry:
                        log_entry = AutomationLog(
                            rule_code=rule_code,
                            name=f"Autonomous Reorder ({target_id})",
                            trigger=f"Autonomous background sweep: stock below reorder point",
                            action=f"{'Pending Approval' if is_high_impact else 'Auto-Executed'}: Reorder {qty} units",
                            status=status_str,
                            executions_today=1
                        )
                        db.add(log_entry)
                        db.flush()
                    else:
                        log_entry.status = status_str
                        log_entry.executions_today += 1


                    actions_triggered.append({
                        "agent": "AG-02 Inventory Agent",
                        "type": "REORDER",
                        "target_id": target_id,
                        "status": status_str,
                        "quantity": qty
                    })

                # Update Inventory Agent Activity
                act = db.query(AgentActivity).filter(AgentActivity.agent_code == "AG-02").first()
                if act:
                    act.tasks_processed += 1
                    act.action = f"autonomous sweep checked {len(low_stock_items)} low-stock items."
                    act.time_ago = "Just now"
        except Exception as e:
            logger.warning(f"Autonomous sweep inventory check warning: {e}")

        # 2. Near-expiry sweep (Wastage Agent AG-03)
        try:
            near_expiry = WastageService.get_near_expiry_items(db)
            if near_expiry:
                reasoning.append(f"Detected {len(near_expiry)} near-expiry item(s).")
                for idx, item in enumerate(near_expiry[:5]):
                    item_code = getattr(item, "item_code", "SKU-EXP")
                    disc_pct = 25.0
                    rule_code = f"AUT-DISC-{item_code}-{idx+1}"
                    is_high_impact = disc_pct > 30.0
                    status_str = "PENDING_APPROVAL" if is_high_impact else "EXECUTED"

                    log_entry = db.query(AutomationLog).filter(AutomationLog.rule_code == rule_code).first()
                    if not log_entry:
                        log_entry = AutomationLog(
                            rule_code=rule_code,
                            name=f"Autonomous Markdown ({item_code})",
                            trigger=f"Autonomous background sweep: perishable expiry near threshold",
                            action=f"{'Pending Approval' if is_high_impact else 'Auto-Executed'}: {disc_pct}% promo markdown",
                            status=status_str,
                            executions_today=1
                        )
                        db.add(log_entry)
                        db.flush()
                    else:
                        log_entry.status = status_str
                        log_entry.executions_today += 1


                    actions_triggered.append({
                        "agent": "AG-03 Wastage Agent",
                        "type": "DISCOUNT",
                        "target_id": item_code,
                        "status": status_str,
                        "discount_pct": disc_pct
                    })
        except Exception as e:
            logger.warning(f"Autonomous sweep wastage check warning: {e}")

        # 3. Upcoming festival sweep (Forecast Agent AG-01)
        try:
            festivals = FestivalForecastService.get_upcoming_festivals("General", within_days=60)
            if festivals:
                reasoning.append(f"Detected {len(festivals)} upcoming Indian festival surge event(s).")
        except Exception as e:
            logger.warning(f"Autonomous sweep festival check warning: {e}")

        db.commit()

        # Add agent trace to pipeline_state
        pipeline_state.add_agent_trace(
            agent_id="AG-SCHEDULER",
            agent_name="Autonomous Background Scheduler",
            task="Background periodic supply chain monitoring sweep",
            reasoning_steps=reasoning or ["Autonomous background sweep completed with zero critical anomalies."],
            tools_executed=[{"tool": "run_autonomous_sweep", "actions_triggered": len(actions_triggered)}],
            status="SUCCESS",
            details={"actions_triggered": actions_triggered}
        )

        return {
            "status": "SUCCESS",
            "sweep_timestamp": self.last_sweep_time.isoformat(),
            "sweeps_completed": self.sweeps_completed,
            "actions_triggered_count": len(actions_triggered),
            "actions_triggered": actions_triggered,
            "reasoning": reasoning
        }


# Singleton instance
autonomous_scheduler = AutonomousAgentScheduler()
