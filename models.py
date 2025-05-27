# models.py
from typing import TypedDict, Annotated, Sequence, List, Dict, Any
import operator
from langchain_core.messages import HumanMessage

class AgentState(TypedDict, total=False):
    """State definition for the simulation workflow."""
    conversation_history: Annotated[Sequence[HumanMessage], operator.add]
    requirements_summary: str
    simulation_plan: str
    generated_code: str
    validation_errors: List[str]
    test_results: Dict[str, Any]
    final_output: Dict[str, Any]