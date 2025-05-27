# app.py
from langchain_core.messages import HumanMessage
from models import AgentState
from agents import create_requirement_elicitor_agent
from workflow import build_workflow

def run_simulation_workflow():
    """Run the interactive simulation workflow."""
    print("=== Production System Simulation Assistant ===")
    print("I'll help you create a SimPy model of your manufacturing/logistics system.\n")
    
    # Initialize state
    state = {
        "conversation_history": [],
        "requirements_summary": "",
        "simulation_plan": "",
        "generated_code": "",
        "validation_errors": [],
        "test_results": {},
        "final_output": None
    }
    
    # Requirement Elicitation Phase
    elicitor = create_requirement_elicitor_agent()
    print("Please describe your production system including:")
    print("- Processing steps and sequence")
    print("- Machines and their counts")
    print("- Storage areas and capacities")
    print("- Key metrics you want to track\n")
    
    while not state["requirements_summary"]:
        response = elicitor.invoke({
            "conversation_history": state["conversation_history"]
        })
        
        # Check if this is a complete summary with all required sections
        required_sections = [
            "Production System Description",
            "Key Resources",
            "Key Entities",
            "Process Flow",
            "Processing Times",
            "Simulation Goals and KPIs"
        ]
        
        is_complete_summary = all(section in response for section in required_sections)
        
        if is_complete_summary:
            print("\n=== Requirements Summary ===")
            print(response)
            confirm = input("\nDoes this look correct? (y/n): ")
            if confirm.lower() == 'y':
                state["requirements_summary"] = response
                print("\nGenerating simulation...")
            else:
                correction = input("What needs correction? ")
                state["conversation_history"].append(
                    HumanMessage(content=f"Correction: {correction}"))
        else:
            print(f"\nAgent: {response}")
            user_input = input("Your response: ")
            state["conversation_history"].append(
                HumanMessage(content=user_input))
    
    # Prepare initial workflow state
    workflow_state = {
        "conversation_history": state["conversation_history"],
        "requirements_summary": state["requirements_summary"],
        "simulation_plan": "",
        "generated_code": "",
        "validation_errors": [],
        "test_results": {},
        "final_output": None
    }
    
    # Build and execute workflow
    print("\n=== Starting Simulation Generation ===")
    app = build_workflow()
    final_state = None
    
    # Set recursion limit
    config = {"recursion_limit": 50}
    
    # Stream through the workflow and capture the final state
    for output in app.stream(workflow_state):
        # Extract state and node information
        if "state" in output:
            current_state = output["state"]
            current_node = output.get("node")
        else:
            # For compatibility with different LangGraph versions
            current_node = next(iter(output.keys())) if output else None
            if current_node:
                current_state = output[current_node]
            else:
                continue  # Skip if we can't determine the node
        
        if current_node:
            print(f"\n=== {current_node.replace('_', ' ').title()} ===")
            # Print more detailed information about the current state for debugging
            print(f"Current state keys: {list(current_state.keys())}")
        
        if current_state.get("simulation_plan") and current_node == "simulation_planning":
            print("\nSimulation Plan created.")
            print(f"Plan length: {len(current_state['simulation_plan'])}")
        
        if current_state.get("generated_code") and current_node == "code_generation":
            print("\nGenerated Code Preview:")
            code_preview = current_state["generated_code"][:500] + "..." if len(current_state["generated_code"]) > 500 else current_state["generated_code"]
            print(code_preview)
        
        if current_state.get("validation_errors") is not None and current_node == "code_validation":
            if current_state["validation_errors"]:
                print("\nValidation Issues Found:")
                for error in current_state["validation_errors"]:
                    print(f"- {error}")
            else:
                print("\nCode Validation Passed!")
        
        if current_state.get("test_results") and current_node == "scenario_testing":
            print("\nTest Results:")
            print(f"Status: {current_state['test_results'].get('status', 'Unknown')}")
            if current_state['test_results'].get('metrics'):
                print("Metrics:")
                for key, value in current_state['test_results']['metrics'].items():
                    print(f"  {key}: {value}")
        
        if current_state.get("final_output") and current_node == "generate_final_output":
            print("\n=== Simulation Complete ===")
            if current_state["final_output"].get("analysis"):
                print("\nAnalysis:")
                print(current_state["final_output"]["analysis"])
        
        # Update final state
        final_state = current_state
    
    # Add a fallback mechanism if the graph isn't progressing
    if not final_state or (final_state.get("requirements_summary") and not final_state.get("simulation_plan")):
        print("\n=== Using Direct Agent Execution ===")
        print("The workflow graph didn't progress. Running agents directly...")
        
        # Start with the requirements we already have
        final_state = {
            "conversation_history": state["conversation_history"],
            "requirements_summary": state["requirements_summary"],
            "simulation_plan": "",
            "generated_code": "",
            "validation_errors": [],
            "test_results": {},
            "final_output": None
        }
        
        # Directly execute the simulation plan agent
        print("\n=== Generating Simulation Plan ===")
        from agents import create_simulation_plan_agent
        planner = create_simulation_plan_agent()
        simulation_plan = planner.invoke({"requirements_summary": final_state["requirements_summary"]})
        final_state["simulation_plan"] = simulation_plan
        print("Simulation plan generated successfully!")
        
        # Directly execute the code generator agent
        print("\n=== Generating Simulation Code ===")
        from agents import create_code_generator_agent
        generator = create_code_generator_agent()
        generated_code = generator.invoke({"simulation_plan": final_state["simulation_plan"]})
        final_state["generated_code"] = generated_code
        print("Simulation code generated successfully!")
        
        # We'll skip validation and testing in this fallback path
        final_state["final_output"] = {
            "code": final_state["generated_code"],
            "analysis": "Generated through direct agent execution (fallback path)."
        }
    
    # Make sure final_state is properly initialized
    if not final_state:
        print("\nWarning: No final state was captured.")
        return None
    
    # Extract simulation code from final state
    final_code = None
    if final_state.get("final_output") and final_state["final_output"].get("code"):
        final_code = final_state["final_output"]["code"]
    elif final_state.get("generated_code"):
        final_code = final_state["generated_code"]
    
    # Handle file saving if code was generated
    if final_code:
        # Create the simulation-models directory if it doesn't exist
        import os
        from datetime import datetime
        
        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
    
        # Create save directory path relative to the script location
        save_dir = os.path.join(script_dir, "simulation-models")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            print(f"Created directory: {save_dir}")
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
        filename = f"{timestamp}-simulation-model.py"
        filepath = os.path.join(save_dir, filename)
        
        # Save the file
        try:
            with open(filepath, 'w') as f:
                f.write(final_code)
            print(f"\nSimulation model saved to: {filepath}")
            print(f"Run with: python {filepath}")
        except Exception as e:
            print(f"Error saving file: {e}")
            print("Displaying code preview instead:")
            print("\n--- SIMULATION CODE PREVIEW (first 1000 chars) ---")
            print(final_code[:1000] + "..." if len(final_code) > 1000 else final_code)
            print("---------------------")
    else:
        print("\nNo simulation code was generated to save.")
    
    return final_state.get("final_output")

if __name__ == "__main__":
    final_result = run_simulation_workflow()