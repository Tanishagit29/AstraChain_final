import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseSupplyChainAgent(ABC):
    """
    Abstract base class for autonomous Agentic AI sub-agents in TransitOps.
    Holds system prompt and OpenAI-style tool schemas (schema + Python callable handler).
    Exposes run(task, context) implementing a ReAct tool-calling loop using Groq.
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
        api_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None)
        if not api_key:
            return None
        try:
            from groq import Groq
            return Groq(api_key=api_key)
        except ImportError:
            logger.warning("groq Python package not installed.")
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize Groq client: {e}")
            return None

    def _call_groq_with_retry(
        self,
        client: Any,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 3,
    ) -> Any:
        """
        Invokes Groq chat.completions.create with exponential backoff for rate limits.
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
                err_msg = str(e).lower()
                is_rate_limit = "429" in err_msg or "rate limit" in err_msg or "too many requests" in err_msg
                if is_rate_limit and attempt < max_retries - 1:
                    sleep_sec = (2 ** attempt) + 0.5
                    logger.warning(f"Groq rate limit hit on attempt {attempt + 1}. Retrying in {sleep_sec}s...")
                    time.sleep(sleep_sec)
                else:
                    raise e

    def run(self, task: str, context: Optional[Dict[str, Any]] = None, max_steps: int = 5) -> Dict[str, Any]:
        """
        ReAct-style autonomous execution loop:
        1. Calls Groq chat.completions with system prompt, task context, and tool schemas.
        2. If LLM returns tool_calls, executes matched Python handler(s).
        3. Appends tool results as role="tool" messages with tool_call_id.
        4. Repeats up to max_steps (default 5).
        5. Returns final response text, tools executed, and reasoning traces.
        """
        context = context or {}
        db = context.get("db")

        messages: List[Dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        user_content = f"Task: {task}"
        context_str_parts = []
        for k, v in context.items():
            if k != "db":
                context_str_parts.append(f"{k}: {v}")
        if context_str_parts:
            user_content += f"\nContext:\n" + "\n".join(context_str_parts)

        messages.append({"role": "user", "content": user_content})

        tools_executed: List[Dict[str, Any]] = []
        reasoning_steps: List[str] = []

        client = self._get_groq_client()
        if not client:
            # Fallback path if GROQ_API_KEY is not configured
            logger.info(f"GROQ_API_KEY absent. Executing fallback path for agent {self.name}.")
            return self.fallback_execute(task, context)

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

                choice = response.choices[0]
                msg = choice.message
                content = msg.content or ""

                tool_calls = getattr(msg, "tool_calls", None)

                if not tool_calls:
                    final_content = content
                    reasoning_steps.append(f"Step {step}: LLM produced final response.")
                    break

                # Assistant made tool call(s)
                tool_calls_serialized = []
                for tc in tool_calls:
                    tool_calls_serialized.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    })

                assistant_msg = {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls_serialized,
                }
                messages.append(assistant_msg)

                # Process each tool call
                for tc in tool_calls:
                    fn_name = tc.function.name
                    raw_args = tc.function.arguments
                    try:
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        args = {}

                    reasoning_steps.append(f"Step {step}: Tool call '{fn_name}' with args {args}")

                    handler = self._tool_handlers.get(fn_name)
                    if handler:
                        try:
                            # Invoke handler with db if needed
                            if db is not None:
                                tool_result = handler(db=db, **args)
                            else:
                                tool_result = handler(**args)
                        except TypeError:
                            # Handler might not accept db or kwargs strictly
                            tool_result = handler(**args)
                        except Exception as ex:
                            tool_result = {"error": f"Tool execution failed: {str(ex)}"}
                    else:
                        tool_result = {"error": f"Tool '{fn_name}' not found."}

                    tools_executed.append({
                        "step": step,
                        "tool": fn_name,
                        "arguments": args,
                        "result": tool_result,
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_result, default=str),
                    })

            if not final_content and step >= max_steps:
                final_content = "ReAct loop reached maximum step limit without final conclusion."

        except Exception as e:
            logger.error(f"Error during ReAct execution in agent {self.name}: {e}")
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
