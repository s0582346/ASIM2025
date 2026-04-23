# nodes.py
import os
import tempfile
import subprocess
import pylint.lint
from langchain_core.messages import HumanMessage
from models import AgentState
from agents import (
    create_requirement_elicitor_agent,
    create_simulation_plan_agent,
    create_code_generator_agent,
    create_code_validator_agent,
    create_scenario_tester_agent
)
from usage_tracker import usage_tracker

def requirement_elicitation_node(state: AgentState):
    """Node that handles requirement elicitation."""
    # Create a callback for tracking token usage
    callback = usage_tracker.get_callback_for_agent("requirement_elicitor")

    # Create agent
    elicitor = create_requirement_elicitor_agent(callbacks=[callback])

    conversation_history = state.get("conversation_history", [])
    if not conversation_history:
        conversation_history = [
            HumanMessage(
                content=(
                    "I am ready to describe my production system. "
                    "Please ask your first elicitation question."
                )
            )
        ]
    
    # Invoke the agent
    result = elicitor.invoke({
        "conversation_history": conversation_history
    })
    
    # Log the token usage
    usage_tracker.log_usage_from_callback("requirement_elicitor", callback, {
        "state_keys": list(state.keys()),
        "result_length": len(result)
    })

    # Check if the result contains a complete requirements summary with all required sections
    required_sections = [
        "Production System Description",
        "Key Resources",
        "Key Entities", 
        "Process Flow",
        "Processing Times",
        "Simulation Goals and KPIs"
    ]
    
    is_complete_summary = all(section in result for section in required_sections)
    
    # If this is a complete summary with all required sections, save it
    if is_complete_summary:
        return {"requirements_summary": result}
    
    # Otherwise, continue the conversation
    return {"conversation_history": [HumanMessage(content=result)]}

def simulation_plan_node(state: AgentState):
    """Node that generates a simulation plan."""
    # Create a callback for tracking token usage
    callback = usage_tracker.get_callback_for_agent("simulation_plan")

    # Create agent with callback
    planner = create_simulation_plan_agent(callbacks=[callback])

    # Invoke the agent
    result = planner.invoke({
        "requirements_summary": state["requirements_summary"]
    })

    # Log the token usage
    usage_tracker.log_usage_from_callback("simulation_plan", callback, {
        "requirements_length": len(state["requirements_summary"]),
        "plan_length": len(result)
    })

    return {"simulation_plan": result}

def code_generation_node(state: AgentState):
    """Node that generates simulation code."""
    # Create a callback for tracking token usage
    callback = usage_tracker.get_callback_for_agent("code_generator")

    generator = create_code_generator_agent(callbacks=[callback])
    # Invoke the agent
    raw_response = generator.invoke({
        "simulation_plan": state["simulation_plan"]
    })

    # Log the token usage
    usage_tracker.log_usage_from_callback("code_generator", callback, {
        "plan_length": len(state["simulation_plan"]),
        "response_length": len(raw_response)
    })
    
    # Extract code from the LLM's response (which might include markdown code blocks)
    generated_code = ""
    
    # Check if the response contains code blocks
    if "```python" in raw_response:
        # Extract code from Python code blocks
        code_blocks = raw_response.split("```python")
        for block in code_blocks[1:]:  # Skip the part before the first code block
            if "```" in block:
                # Extract the code part (before the closing ```)
                generated_code += block.split("```")[0] + "\n"
            else:
                # If there's no closing ```, take the whole block
                generated_code += block + "\n"
    elif "```" in raw_response:
        # Try to extract code from generic code blocks
        code_blocks = raw_response.split("```")
        # Take even-indexed blocks (inside ```)
        for i in range(1, len(code_blocks), 2):
            if i < len(code_blocks):
                generated_code += code_blocks[i] + "\n"
    else:
        # If no code blocks, assume the entire response is code
        # (but skip any explanatory text at the beginning)
        lines = raw_response.split("\n")
        start_idx = 0
        # Skip explanatory text until we find what looks like a code line
        for i, line in enumerate(lines):
            if line.strip().startswith("import ") or line.strip().startswith("from ") or line.strip().startswith("class ") or line.strip().startswith("def "):
                start_idx = i
                break
        generated_code = "\n".join(lines[start_idx:])
    
    # Create debug directory if it doesn't exist
    import os        
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Create save directory path relative to the script location
    debug_dir = os.path.join(script_dir, "debug-output")
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    # Save the code for debugging
    with open(os.path.join(debug_dir, "generated_code.py"), "w") as f:
        f.write(generated_code)
        
    print(f"Generated code length: {len(generated_code)} characters")
    print(f"Generated code starts with: {generated_code[:100]}...")
    
    return {"generated_code": generated_code}

def code_validation_node(state: AgentState):
    """Node that validates the generated code, focusing only on critical execution-blocking issues."""
    # Check if we have a code to validate
    if not state.get("generated_code"):
        return {"validation_errors": ["No code to validate"]}

    # Run static analysis for syntax errors
    static_errors = run_static_analysis(state["generated_code"])

    # Create a callback for the validator
    callback = usage_tracker.get_callback_for_agent("code_validator")
    
    # Run the LLM validator for deeper analysis
    validator = create_code_validator_agent(callbacks=[callback])
    feedback = validator.invoke({
        "requirements_summary": state["requirements_summary"],
        "generated_code": state["generated_code"]
    })
    
    # Log the token usage
    usage_tracker.log_usage_from_callback("code_validator", callback, {
        "validation_status": "passed" if feedback.startswith("VALIDATION PASSED") else "failed",
        "code_length": len(state["generated_code"])
    })


    # Consolidate errors
    errors = []
    
    # Add syntax errors if any were found
    if static_errors:
        errors.append(f"Syntax errors:\n{static_errors}")
    
    # Add LLM validation feedback if it didn't pass
    if not feedback.startswith("VALIDATION PASSED"):
        errors.append(feedback)
    
    # Return the results - empty errors list means validation passed
    return {"validation_errors": errors}


def scenario_testing_node(state: AgentState):
    """Node that tests the simulation code."""
    # Create a temporary file for the code
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as tmp:
        tmp.write(state["generated_code"])
        tmp_path = tmp.name
    
    try:
        # Run the simulation
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Parse results
        metrics = {}
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if ":" in line:
                    key, val = line.split(":", 1)
                    metrics[key.strip()] = val.strip()
            return {"test_results": {"status": "SUCCESS", "metrics": metrics}}
        return {"test_results": {"status": "ERROR", "error": result.stderr}}
    except Exception as e:
        return {"test_results": {"status": "EXCEPTION", "error": str(e)}}
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# cleaner approach, use when debugging finished
#def final_output_node(state: AgentState):
#    """Node that generates the final output."""
#    # Debug print to verify state
#    print(f"Final output node state keys: {list(state.keys())}")
#    
#    tester = create_scenario_tester_agent()
#    analysis = tester.invoke({
#        "requirements_summary": state.get("requirements_summary", "No requirements provided"),
#        "test_results": state.get("test_results", {})
#    })
#    return {"final_output": {
#        "code": state.get("generated_code", ""),
#        "test_results": state.get("test_results", {}),
#        "analysis": analysis
#    }}


def final_output_node(state: AgentState):
    """Node that generates the final output."""
    # Log the state keys for debugging
    print(f"Final output node state keys: {list(state.keys())}")
    
    # Check if required keys exist
    if "requirements_summary" not in state:
        print("WARNING: requirements_summary missing from state!")
        requirements = "No requirements provided - STATE ERROR"
    else:
        requirements = state["requirements_summary"]
        
    if "test_results" not in state:
        print("WARNING: test_results missing from state!")
        test_results = {"status": "UNKNOWN", "error": "Missing from state"}
    else:
        test_results = state["test_results"]

    # Create a callback for tracking token usage
    callback = usage_tracker.get_callback_for_agent("scenario_tester")
    
    # Use the variables we've now safely extracted
    tester = create_scenario_tester_agent(callbacks=[callback])
    analysis = tester.invoke({
        "requirements_summary": requirements,
        "test_results": test_results
    })

    # Log the token usage
    usage_tracker.log_usage_from_callback("scenario_tester", callback, {
        "analysis_length": len(analysis),
        "test_results_status": test_results.get("status", "UNKNOWN")
    })
    
    
    return {"final_output": {
        "code": state.get("generated_code", ""),
        "test_results": test_results,
        "analysis": analysis
    }}


def run_static_analysis(code: str) -> str:
    """Run static analysis on the generated code, focusing only on critical issues."""
    if not code or len(code.strip()) == 0:
        return "Error: Empty code provided"
    
    # Create debug directory if it doesn't exist
    import os
    import re
    import subprocess
    import tempfile
    debug_dir = "debug-output"
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
        
    # Debug: Save the code being analyzed
    with open(os.path.join(debug_dir, "analysis_input.py"), "w") as f:
        f.write(code)
        
    tmp_path = None
    try:
        # Pre-process code to fix common LLM-generated formatting issues
        try:
            # Step 1: Check if the code is wrapped in a markdown code block
            code_block_pattern = re.compile(r'```(?:python)?\s*(.*?)\s*```', re.DOTALL)
            match = code_block_pattern.match(code.strip())
            
            if match:
                # If the entire content is a code block, extract just the code
                cleaned_code = match.group(1)
            else:
                # Otherwise, start with the original code
                cleaned_code = code
                
            # Handle other common formatting issues
            cleaned_code = (
                cleaned_code                
                .replace('\u2014', '-')  # em dash
                .replace('\u2013', '-')  # en dash
                .replace('\u201C', '"')  # left double quote
                .replace('\u201D', '"')  # right double quote
                .replace('\u2018', "'")  # left single quote
                .replace('\u2019', "'")  # right single quote
                .replace('`', "'")       # backticks
                .replace('```', "")      # markdown code triple backticks

                #.replace('—', '-')  # em dash
                #.replace('–', '-')  # en dash
                #.replace('"', '"')  # left double quote
                #.replace('"', '"')  # right double quote
                #.replace(''', "'")  # left single quote
                #.replace(''', "'")  # right single quote
                #.replace('`', "'")  # backticks
                #.replace('```', "") # markdown code triple backticks
            )
        except Exception as e:
            print(f"Error during code sanitization: {str(e)}")
            cleaned_code = code  # Fall back to original code if sanitization fails
        
        # Save the cleaned code for debugging
        with open(os.path.join(debug_dir, "cleaned_code.py"), "w") as f:
            f.write(cleaned_code)
            
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as tmp:
            tmp.write(cleaned_code)
            tmp_path = tmp.name
            
        print(f"Running static analysis on file: {tmp_path}")
        
        # First, try a quick syntax check with Python's compile function
        try:
            compile(cleaned_code, tmp_path, 'exec')
            print("Basic syntax check passed, running pylint for more detailed analysis")
            
            # If compile passes, run pylint for more detailed feedback
            from pylint.reporters.text import TextReporter
            from io import StringIO
            pylint_output = StringIO()
            
            # Configure pylint to focus only on critical issues
            # Note: Using only valid pylint message IDs
            pylint_opts = [
                '--disable=all',
                '--enable=syntax-error,undefined-variable,used-before-assignment,no-member,not-callable',
                #'--enable=import-error', # package name resolution: import pil but pip install pillow 
                '--errors-only',
                tmp_path
            ]
            
            # Run pylint
            pylint.lint.Run(
                pylint_opts,
                reporter=TextReporter(pylint_output),
                exit=False
            )
            
            # Get the output
            output = pylint_output.getvalue().strip()  
        
            # Returns only meaningful messages due to pylint_opts
            if output:
                return output
            return ""
            
        except SyntaxError as e:
            # If compile fails with a syntax error, return that immediately
            error_msg = f"Line {e.lineno}: {e.msg}"
            print(f"Basic syntax check failed: {error_msg}")
            return error_msg
            
    except Exception as e:
        error_msg = f"Static analysis error: {str(e)}"
        print(error_msg)
        return error_msg
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)