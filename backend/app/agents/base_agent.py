import os
import json
import time
import re
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, Optional, Tuple

from app.core.config import settings

import inspect

logger = logging.getLogger(__name__)


class BaseSupplyChainAgent(ABC):
    """
    Abstract base class for autonomous Agentic AI sub-agents in AstraChain.
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
        self.model = model or getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")

        
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

    def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 7,
        timeout_seconds: float = 60.0,
    ) -> Dict[str, Any]:
        """
        ReAct-style autonomous execution loop with max-step, timeout, and JSON guards:
        1. Checks for GROQ_API_KEY. If missing, returns an explicit error.
        2. Calls Groq chat.completions with system prompt, task context, and tool schemas.
        3. If LLM returns tool_calls, executes matched Python handler(s).
        4. Appends tool results as role="tool" messages with tool_call_id.
        5. Repeats up to max_steps with timeout enforcement.
        6. Returns final response text, tools executed, and reasoning traces.
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
            err_msg = (
                "GROQ_API_KEY is missing or invalid in environment. "
                "Autonomous AI agent execution requires a valid GROQ_API_KEY."
            )
            logger.error(f"Agent {self.name} failed: {err_msg}")
            return {
                "status": "ERROR",
                "error": err_msg,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "final_content": err_msg,
                "tools_executed": [],
                "reasoning_steps": [err_msg],
                "steps": 0,
            }

        step = 0
        final_content = ""
        start_time = time.time()

        try:
            while step < max_steps:
                if time.time() - start_time > timeout_seconds:
                    reasoning_steps.append(f"Timeout guard reached ({timeout_seconds}s). Terminating loop.")
                    final_content = f"Agent execution timed out after {timeout_seconds} seconds."
                    break

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
                    reasoning_steps.append(f"Step {step}: Agent formulated final analytical conclusion.")
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

                # Process each tool call with malformed JSON handling
                for tc in tool_calls:
                    fn_name = tc.function.name
                    raw_args = tc.function.arguments
                    args = {}
                    if raw_args:
                        try:
                            parsed_args = json.loads(raw_args)
                            if isinstance(parsed_args, dict):
                                args = parsed_args
                        except Exception as parse_err:
                            logger.warning(f"Malformed tool call JSON from LLM ({fn_name}): {raw_args}. Error: {parse_err}")
                            try:
                                cleaned_args = re.sub(r',\s*([}\]])', r'\1', raw_args)
                                parsed_cleaned = json.loads(cleaned_args)
                                if isinstance(parsed_cleaned, dict):
                                    args = parsed_cleaned
                            except Exception:
                                args = {}

                    # Remove empty or invalid internal keys
                    clean_args = {k: v for k, v in args.items() if k and not str(k).startswith("_")}

                    reasoning_steps.append(f"Step {step}: Tool call '{fn_name}' with arguments {clean_args}")

                    handler = self._tool_handlers.get(fn_name)
                    if handler:
                        try:
                            sig = inspect.signature(handler)
                            params = sig.parameters
                            has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
                            
                            call_kwargs = {}
                            if "db" in params:
                                if db is not None:
                                    call_kwargs["db"] = db
                            for k, v in clean_args.items():
                                if k in params or has_kwargs:
                                    call_kwargs[k] = v

                            tool_result = handler(**call_kwargs)
                        except Exception as ex:
                            tool_result = {"error": f"Tool '{fn_name}' execution failed: {str(ex)}"}
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
            err_str = str(e)
            logger.error(f"Error during ReAct execution in agent {self.name}: {err_str}")
            return {
                "status": "ERROR",
                "error": err_str,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "final_content": f"Agent execution failed: {err_str}",
                "tools_executed": tools_executed,
                "reasoning_steps": reasoning_steps + [f"Error: {err_str}"],
                "steps": step,
            }

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
        Legacy fallback method interface.
        """
        return {
            "status": "FALLBACK",
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "final_content": f"Fallback executed for task: '{task}'.",
            "tools_executed": [],
            "reasoning_steps": ["Fallback executed."],
            "steps": 0,
        }

    @abstractmethod
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy interface compatibility."""
        pass
