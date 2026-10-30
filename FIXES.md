# AstraChain – Groq integration fixes

## What was wrong
After Groq was added, the CSV upload (`POST /api/data-collection/pipeline`) ran the LLM agents **inside the HTTP request**
(`sync_cleaned_data_to_forecast` → `ForecastAgent / InventoryAgent / WastageAgent`), and the endpoint was `async def`
doing blocking work. Every Groq call (rate limits, retries, timeouts, malformed tool calls) therefore froze the whole API:
the pipeline never returned, `/pipeline/status` stopped answering, and every other page showed nothing.

## What changed
Backend
- `app/agents/base_agent.py` – hard Groq timeout (no hidden SDK retries), circuit breaker (after one LLM failure all agents use the
  deterministic path for 60s), tool-arg coercion, tool-result size cap, DB `rollback()` when a tool fails, `use_llm` switch,
  malformed-tool-call (`tool_use_failed`) handled without disabling the LLM.
- `app/api/routes/data_collection.py` – pipeline body runs in a worker thread (`run_in_threadpool`); in-request agent sync is
  deterministic only; Groq agents start in the background after results are saved.
- `app/services/agent_insights.py` (new) + `GET /api/pipeline/agents` – background Groq agent reasoning, never blocks results.
- `app/services/pipeline_state.py` – `agent_insights` state.
- `app/agents/wastage_agent.py` – LLM path now also returns the structured metrics other endpoints need; nested route handoff is deterministic.
- `app/ai/provider.py`, `app/services/ai_service.py` – Copilot uses the same timeout/breaker, sanitises chat history for Groq,
  and has a `get_pipeline_results` tool so it can answer about the uploaded dataset.
- `app/core/config.py`, `.env.example` – `GROQ_TIMEOUT_SECONDS`, `GROQ_COOLDOWN_SECONDS`.
- Tests: new `tests/test_agent_resilience.py`; `tests/test_wastage_dates.py` no longer hard-codes a late-August "today". 64/64 pass.

Frontend
- `src/api/client.js` – request timeouts, readable error messages (reads `error`/`message`/`detail`), `VITE_API_URL`, `getPipelineAgents`.
- `src/pages/DataIntelligenceAgent.jsx` – "AI Agent Insights" panel (polls until Groq agents finish).

## Run
```
cd backend
pip install -r requirements.txt
# optional, enables LLM agents:  put GROQ_API_KEY="gsk_..." in backend/.env
uvicorn app.main:app --port 8000        # run from the backend/ folder (the .env and SQLite path are relative)

# new terminal, project root
npm install && npm run dev
```
Pipeline results live in server memory: restarting the backend (or `--reload` triggering) clears them, so re-upload the CSV after a restart.
