from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseSupplyChainAgent(ABC):
    """
    Abstract base class for all Agentic AI sub-agents in TransitOps.
    Subclasses will implement LLM reasoning, tool calling, and autonomous decision routines.
    """
    def __init__(self, agent_id: str, name: str, role: str):
        self.agent_id = agent_id
        self.name = name
        self.role = role

    @abstractmethod
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass
