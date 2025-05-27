# workflow.py
from langgraph.graph import StateGraph, END
from models import AgentState # Assuming models.py defines AgentState
from nodes import (
    requirement_elicitation_node,
    simulation_plan_node,
    code_generation_node,
    code_validation_node,
    scenario_testing_node,
    final_output_node
)

def should_retry_code(state: AgentState):
    """Determine if code generation should be retried based on validation errors."""
    # If there are no validation errors, we don't need to retry
    if not state.get("validation_errors"):
        return False

    # Check if there are syntax errors specifically
    for error in state["validation_errors"]:
        if "syntax error" in error.lower():
            return True

    # If no syntax errors but other validation issues, proceed anyway
    # This prevents infinite loops on non-critical issues
    return False

def should_retry_testing(state: AgentState):
    """Determine if testing should be retried based on test results."""
    # Ensure test_results and its 'status' key exist to prevent KeyError
    return state.get("test_results", {}).get("status") != "SUCCESS"

def build_workflow():
    """Build and return the workflow graph."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("requirement_elicitation", requirement_elicitation_node)
    workflow.add_node("simulation_planning", simulation_plan_node)
    workflow.add_node("code_generation", code_generation_node)
    workflow.add_node("code_validation", code_validation_node)
    workflow.add_node("scenario_testing", scenario_testing_node)
    workflow.add_node("generate_final_output", final_output_node)

    # Add direct edges for linear progression
    workflow.add_edge("requirement_elicitation", "simulation_planning")
    workflow.add_edge("simulation_planning", "code_generation")
    workflow.add_edge("code_generation", "code_validation")

    # Add conditional edges for validation feedback loop
    workflow.add_conditional_edges(
        "code_validation",
        should_retry_code,
        {True: "code_generation", False: "scenario_testing"}
    )

    # Add conditional edges for testing feedback loop
    workflow.add_conditional_edges(
        "scenario_testing",
        should_retry_testing,
        {True: "code_generation", False: "generate_final_output"}
    )

    # Add final edge
    workflow.add_edge("generate_final_output", END)

    # Set the entry point
    workflow.set_entry_point("requirement_elicitation")

    # Part below solely for token usage tracking (invoke + stream methods)
    # Compile the workflow
    compiled_workflow = workflow.compile()

    # Import the usage tracker
    from usage_tracker import usage_tracker # Assuming usage_tracker.py exists and works

    # Wrap the stream method (to do: rewrite for invoke, way easier to track token usage)
    original_stream = compiled_workflow.stream
    def wrapped_stream(*args, **kwargs):
        # Using a simple boolean flag
        report_saved = False

        # Yield items from the original stream
        try:
            for item in original_stream(*args, **kwargs):
                yield item
        finally:
            # Ensure the report is saved once the stream iteration is complete
            # This is more robust as it covers both normal completion and errors
            if not report_saved:
                usage_tracker.save_usage_report()
                report_saved = True # Not strictly necessary here, but good practice if more logic followed

    # Replace the stream method
    compiled_workflow.stream = wrapped_stream

    return compiled_workflow