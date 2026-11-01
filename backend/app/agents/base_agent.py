import os
import json
import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tool results are sent back to the LLM; keep them small so we never blow Groq's
# tokens-per-minute / request-size limits (which makes the call fail and stalls the agent).
MAX_TOOL_RESULT_CHARS = 4000


class LLMCircuitBreaker:
    """
    Process-wide guard around the Groq API.

    When Groq times out, rate-limits us hard, rejects the key, or is unreachable, every agent would
    otherwise wait for its own timeout in turn. After the first failure we skip the LLM for a short
    cooldown and let agents use their deterministic fallback instead.
    """

    def __init__(self) -> None:
        self._open_until = 0.0
        self.last_error: Optional[str] = None
        self._lock = threading.Lock()

    @property
    def cooldown(self) -> float:
        return float(getattr(settings, "GROQ_COOLDOWN_SECONDS", 60.0))

    def is_open(self) -> bool:
        return time.monotonic() < self._open_until

    def trip(self, error: Any) -> None:
        with self._lock:
            self._open_until = time.monotonic() + self.cooldown
            self.last_error = str(error)[:300]
        logger.warning(
            f"Groq LLM disabled for {self.cooldown:.0f}s (deterministic fallback in use): {self.last_error}"
        )

    def reset(self) -> None:
        with self._lock:
            self._open_until = 0.0
            self.last_error = None


llm_breaker = LLMCircuitBreaker()


def get_groq_api_key() -> Optional[str]:
    return os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None) or None


def llm_available() -> bool:
    """True when a Groq key is configured and the circuit breaker is not open."""
    return bool(get_groq_api_key()) and not llm_breaker.is_open()


def make_groq_client():
    """Build a Groq client with a hard timeout and no hidden SDK retries (we handle retries ourselves)."""
    api_key = get_groq_api_key()
    if not api_key:
        return None
    try:
        from groq import Groq
        return Groq(
            api_key=api_key,
            timeout=float(getattr(settings, "GROQ_TIMEOUT_SECONDS", 20.0)),
            max_retries=0,
        )
    except ImportError:
        logger.warning("groq Python package not installed.")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Groq client: {e}")
        return None


def is_tool_format_error(err: Exception) -> bool:
    """Llama models occasionally emit malformed tool calls; Groq answers 400 'tool_use_failed'. Not an outage."""
    msg = str(err).lower()
    return "tool_use_failed" in msg or "failed to call a function" in msg or "failed_generation" in msg


def is_rate_limit_error(err: Exception) -> bool:
    msg = str(err).lower()
    return "429" in msg or "rate limit" in msg or "rate_limit" in msg or "too many requests" in msg


def coerce_tool_args(schema: Dict[str, Any], args: Any) -> Dict[str, Any]:
    """
    LLMs often send "30" for an integer, null for optional values, or invent extra keys.
    Clean the arguments against the tool's JSON schema so the Python handler does not crash.
    """
    if not isinstance(args, dict):
        return {}
    props = (schema.get("function", {}).get("parameters", {}) or {}).get("properties", {}) or {}
    cleaned: Dict[str, Any] = {}
    for key, value in args.items():
        if key not in props or value is None:
            continue
        wanted = props[key].get("type")
        try:
            if wanted == "integer":
                value = int(float(value))
            elif wanted == "number":
                value = float(value)
            elif wanted == "string":
                value = str(value)
            elif wanted == "boolean" and isinstance(value, str):
                value = value.strip().lower() in ("1", "true", "yes")
        except (TypeError, ValueError):
            continue
        cleaned[key] = value
    return cleaned


def serialize_tool_result(result: Any, limit: int = MAX_TOOL_RESULT_CHARS) -> str:
    """JSON-encode a tool result for the LLM, shrinking long lists first and truncating as a last resort."""
    def shrink(obj: Any, n: int) -> Any:
        if isinstance(obj, list):
            return [shrink(i, n) for i in obj[:n]]
        if isinstance(obj, dict):
            return {k: shrink(v, n) for k, v in obj.items()}
        return obj

    text = json.dumps(result, default=str)
    if len(text) <= limit:
        return text
    for n in (25, 10, 5, 3):
        text = json.dumps(shrink(result, n), default=str)
        if len(text) <= limit:
            return text
    return text[:limit] + '..."[truncated]"'


class BaseSupplyChainAgent(ABC):
    """
    Abstract base class for autonomous Agentic AI sub-agents in AstraChain.
    Holds system prompt and OpenAI-style tool schemas (schema + Python callable handler).
    Exposes run(task, context) implementing a ReAct tool-calling loop using Groq.

    Reliability rules:
      * `use_llm = False` forces the deterministic path (used by the upload pipeline, which must never wait on an LLM).
      * Groq calls have a hard timeout; after a failure all agents use the deterministic fallback for a cooldown.
      * run() never raises because of the LLM: any failure ends in `fallback_execute`.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        system_prompt: str = "",
        model: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model or getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        self.use_llm: bool = True

        # Tools store tuples of (schema_dict, callable_handler)
        self._tool_schemas: List[Dict[str, Any]] = []
        self._tool_handlers: Dict[str, Callable] = {}

    def register_tool(self, schema: Dict[str, Any], handler: Callable) -> None:
        """
        Registers an OpenAI-style tool schema and its Python callable handler.
        schema format: {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
        """
        func_name = schema["function"]["name"]
        self._tool_schemas.append(schema)
        self._tool_handlers[func_name] = handler

    def _get_groq_client(self):
        if not self.use_llm or llm_breaker.is_open():
            return None
        return make_groq_client()

    def _call_groq_with_retry(
        self,
        client: Any,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 2,
    ) -> Any:
        """
        Invokes Groq chat.completions.create, retrying briefly on rate limits.
        Waits are short on purpose: an agent must not hold a request open for minutes.
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        for attempt in range(max_retries):
            try:
                return client.chat.completions.create(**kwargs)
            except Exception as e:
                if is_rate_limit_error(e) and attempt < max_retries - 1:
                    sleep_sec = (2 ** attempt) + 0.5
                    logger.warning(f"Groq rate limit hit on attempt {attempt + 1}. Retrying in {sleep_sec}s...")
                    time.sleep(sleep_sec)
                else:
                    raise

    def _execute_tool(self, fn_name: str, raw_args: Any, db: Any) -> Dict[str, Any]:
        """Run one tool call safely. Always returns a JSON-serializable result; never raises."""
        handler = self._tool_handlers.get(fn_name)
        if handler is None:
            return {"error": f"Tool '{fn_name}' not found."}

        try:
            parsed = json.loads(raw_args) if isinstance(raw_args, str) and raw_args else (raw_args or {})
        except json.JSONDecodeError:
            parsed = {}

        schema = next((s for s in self._tool_schemas if s["function"]["name"] == fn_name), {})
        args = coerce_tool_args(schema, parsed)

        try:
            return handler(db=db, **args) if db is not None else handler(**args)
        except Exception as ex:
            # A failed flush leaves the SQLAlchemy session unusable until rolled back.
            if db is not None:
                try:
                    db.rollback()
                except Exception:
                    pass
            logger.warning(f"Tool '{fn_name}' failed in agent {self.name}: {ex}")
            return {"error": f"Tool execution failed: {str(ex)}"}

    def run(self, task: str, context: Optional[Dict[str, Any]] = None, max_steps: int = 5) -> Dict[str, Any]:
        """
        ReAct-style autonomous execution loop:
        1. Calls Groq chat.completions with system prompt, task context, and tool schemas.
        2. If LLM returns tool_calls, executes matched Python handler(s).
        3. Appends tool results as role="tool" messages with tool_call_id.
        4. Repeats up to max_steps (default 5).
        5. Returns final response text, tools executed, and reasoning traces.
        Falls back to the deterministic implementation if the LLM is unavailable or fails.
        """
        context = context or {}
        db = context.get("db")

        client = self._get_groq_client()
        if not client:
            logger.info(f"LLM unavailable/disabled. Executing deterministic path for agent {self.name}.")
            return self.fallback_execute(task, context)

        messages: List[Dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        user_content = f"Task: {task}"
        context_str_parts = [f"{k}: {v}" for k, v in context.items() if k != "db"]
        if context_str_parts:
            user_content += "\nContext:\n" + "\n".join(context_str_parts)
        messages.append({"role": "user", "content": user_content})

        tools_executed: List[Dict[str, Any]] = []
        reasoning_steps: List[str] = []
        step = 0
        final_content = ""

        try:
            while step < max_steps:
                step += 1
                response = self._call_groq_with_retry(
                    client=client,
                    messages=messages,
                    tools=self._tool_schemas if self._tool_schemas else None,
                )

                msg = response.choices[0].message
                content = msg.content or ""
                tool_calls = getattr(msg, "tool_calls", None)

                if not tool_calls:
                    final_content = content
                    reasoning_steps.append(f"Step {step}: LLM produced final response.")
                    break

                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                        }
                        for tc in tool_calls
                    ],
                })

                for tc in tool_calls:
                    fn_name = tc.function.name
                    raw_args = tc.function.arguments
                    tool_result = self._execute_tool(fn_name, raw_args, db)
                    reasoning_steps.append(f"Step {step}: Tool call '{fn_name}' with args {raw_args or '{}'}")

                    try:
                        logged_args = json.loads(raw_args) if raw_args else {}
                    except (json.JSONDecodeError, TypeError):
                        logged_args = {}
                    tools_executed.append({
                        "step": step,
                        "tool": fn_name,
                        "arguments": logged_args,
                        "result": tool_result,
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": serialize_tool_result(tool_result),
                    })

            if not final_content and step >= max_steps:
                final_content = "ReAct loop reached maximum step limit without final conclusion."

        except Exception as e:
            if is_tool_format_error(e):
                logger.warning(f"Agent {self.name}: model produced a malformed tool call ({e}); using deterministic path.")
            else:
                llm_breaker.trip(e)
            return self.fallback_execute(task, context)

        return {
            "status": "SUCCESS",
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "final_content": final_content,
            "tools_executed": tools_executed,
            "reasoning_steps": reasoning_steps,
            "steps": step,
        }

    def fallback_execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback execution method if Groq API is unavailable or missing.
        Subclasses can override this to provide deterministic execution.
        """
        return {
            "status": "FALLBACK",
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "final_content": f"Groq LLM offline or unconfigured. Fallback executed for task: '{task}'.",
            "tools_executed": [],
            "reasoning_steps": ["Groq API unavailable; returned deterministic fallback."],
            "steps": 0,
        }

    @abstractmethod
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy interface compatibility."""
        pass
