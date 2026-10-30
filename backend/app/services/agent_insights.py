"""
LLM Agent Insights
==================
The upload pipeline (clean -> forecast -> inventory -> wastage) is fully deterministic, so results appear
immediately no matter what the LLM is doing.

After it finishes, this module optionally runs the Groq-powered agents (Forecast, Inventory, Wastage) in a
background thread with their own DB session. Their reasoning is stored in `pipeline_state.agent_insights`
and served by `GET /api/pipeline/agents`. If Groq is missing, slow, rate limited or down, the insights are
marked `skipped`/`error` and nothing else is affected.
"""

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.base_agent import llm_available, llm_breaker, get_groq_api_key
from app.core.logging import logger
from app.services.pipeline_state import pipeline_state


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summarize(agent_result: Dict[str, Any]) -> Dict[str, Any]:
    tools = agent_result.get("tools_executed") or []
    used_llm = agent_result.get("status") != "FALLBACK"
    summary = (agent_result.get("final_content") or "").strip()
    if not used_llm:
        reasons = agent_result.get("reasoning_steps") or []
        summary = summary or (reasons[0] if reasons else "Deterministic agent logic was used.")
    return {
        "agent_id": agent_result.get("agent_id"),
        "agent_name": agent_result.get("agent_name"),
        "mode": "llm" if used_llm else "deterministic",
        "summary": summary[:1200],
        "tools_used": [t.get("tool") for t in tools],
        "reasoning_steps": (agent_result.get("reasoning_steps") or [])[:8],
    }


def run_agent_insights(dataset_id: Optional[str], first_sku: Optional[str]) -> None:
    """Worker body. Uses its own DB session and never raises."""
    from app.database.session import SessionLocal
    from app.agents.forecast_agent import ForecastAgent
    from app.agents.inventory_agent import InventoryAgent
    from app.agents.wastage_agent import WastageAgent

    db = SessionLocal()
    agents: List[Dict[str, Any]] = []
    try:
        plan = [
            (ForecastAgent(), lambda a: a.execute(db, product_id=first_sku or "MK-001-F", horizon_days=30)),
            (InventoryAgent(), lambda a: a.execute(db)),
            (WastageAgent(), lambda a: a.execute(db)),
        ]
        for agent, call in plan:
            if pipeline_state.dataset_id != dataset_id:
                return  # a newer upload replaced this run; drop the stale insights
            try:
                agents.append(_summarize(call(agent)))
            except Exception as err:
                db.rollback()
                logger.warning(f"Agent insight failed for {agent.name}: {err}")
                agents.append({
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "mode": "error",
                    "summary": f"Agent failed: {err}",
                    "tools_used": [],
                    "reasoning_steps": [],
                })
            pipeline_state.set_agent_insights(agents=list(agents))

        if pipeline_state.dataset_id != dataset_id:
            return
        used_llm = any(a["mode"] == "llm" for a in agents)
        message = (
            "Groq agents analysed the pipeline results."
            if used_llm
            else f"Groq was unavailable ({llm_breaker.last_error or 'no response'}); deterministic agents were used."
        )
        pipeline_state.set_agent_insights(status="completed", message=message, finished_at=_now(), agents=agents)
    except Exception as err:
        logger.error(f"Agent insights worker crashed: {err}")
        pipeline_state.set_agent_insights(status="error", message=str(err), finished_at=_now(), agents=agents)
    finally:
        db.close()


def launch_agent_insights(first_sku: Optional[str] = None) -> None:
    """Kick off the LLM agents in the background (or mark them skipped). Returns immediately."""
    if not get_groq_api_key():
        pipeline_state.set_agent_insights(
            status="skipped",
            message="GROQ_API_KEY is not set, so only the deterministic agents ran. Add the key to backend/.env to enable LLM agent reasoning.",
            agents=[],
        )
        return
    if not llm_available():
        pipeline_state.set_agent_insights(
            status="skipped",
            message=f"Groq is cooling down after an error ({llm_breaker.last_error}). Pipeline results are unaffected.",
            agents=[],
        )
        return

    dataset_id = pipeline_state.dataset_id
    pipeline_state.set_agent_insights(
        status="running",
        message="Groq agents are analysing your results in the background...",
        started_at=_now(),
        finished_at=None,
        agents=[],
    )
    threading.Thread(
        target=run_agent_insights,
        args=(dataset_id, first_sku),
        name="agent-insights",
        daemon=True,
    ).start()
