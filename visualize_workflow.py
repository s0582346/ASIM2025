#!/usr/bin/env python3
"""
LangGraph Workflow Visualizer

This module provides visualization capabilities for your LangGraph workflow.
Run this file to generate Mermaid diagrams and PNG files of your workflow.

Usage:
    python visualize_workflow.py

The script will:
1. Generate Mermaid syntax that you can copy to https://mermaid.live/
2. Attempt to generate a PNG file using the Mermaid.ink API
3. Save the Mermaid code to a .mmd file for future use
4. Import the .mmd to draw.io 

"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Import your existing workflow components
try:
    from workflow import build_workflow
    print("Successfully imported build_workflow from workflow.py")
except ImportError as e:
    print(f"ERROR: Could not import build_workflow: {e}")
    print("Make sure workflow.py is in the same directory and contains build_workflow() function")
    sys.exit(1)


def generate_mermaid_visualization():
    """
    Generate Mermaid visualization of the workflow.
    
    Returns:
        tuple: (mermaid_code: str, success: bool)
    """
    try:
        # Build your workflow
        print("Building workflow...")
        compiled_workflow = build_workflow()
        
        # Generate Mermaid diagram
        print("Generating Mermaid diagram...")
        mermaid_code = compiled_workflow.get_graph().draw_mermaid()
        
        return mermaid_code, True
        
    except Exception as e:
        print(f"ERROR: Error generating Mermaid diagram: {e}")
        return None, False


def save_mermaid_file(mermaid_code, base_filename="workflow_diagram"):
    """
    Save Mermaid code to a .mmd file with timestamp in diagrams folder.
    
    Args:
        mermaid_code (str): The Mermaid diagram code
        base_filename (str): Base filename (without extension)
        
    Returns:
        bool: Success status
    """
    try:
        # Create diagrams folder if it doesn't exist
        os.makedirs("diagrams", exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
        
        # Create full filename with timestamp and extension
        filename = f"diagrams/{timestamp}-{base_filename}.mmd"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        print(f"Mermaid code saved to '{filename}'")
        return True
    except Exception as e:
        print(f"ERROR: Error saving Mermaid file: {e}")
        return False


def generate_png_visualization(compiled_workflow, base_filename="workflow_diagram"):
    """
    Generate PNG visualization using Mermaid.ink API with timestamp in diagrams folder.
    
    Args:
        compiled_workflow: The compiled LangGraph workflow
        base_filename (str): Base filename (without extension)
        
    Returns:
        bool: Success status
    """
    try:
        print("Generating PNG using Mermaid.ink API...")
        png_data = compiled_workflow.get_graph().draw_mermaid_png()
        
        # Create diagrams folder if it doesn't exist
        os.makedirs("diagrams", exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
        
        # Create full filename with timestamp and extension
        filename = f"diagrams/{timestamp}-{base_filename}.png"
        
        with open(filename, "wb") as f:
            f.write(png_data)
        
        print(f"PNG saved as '{filename}'")
        return True
        
    except Exception as e:
        print(f"ERROR: Error generating PNG: {e}")
        print("NOTE: This might be due to network issues or complex diagram structure")
        return False


def save_analysis_file(analysis_text, base_filename="workflow_diagram"):
    """
    Save analysis text to a .txt file in diagrams folder with timestamp.
    
    Args:
        analysis_text (str): The analysis content to save
        base_filename (str): Base filename (without extension)
        
    Returns:
        bool: Success status
    """
    try:
        # Create diagrams folder if it doesn't exist
        os.makedirs("diagrams", exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
        
        # Create full filename with timestamp and analysis suffix
        filename = f"diagrams/{timestamp}-{base_filename}-analysis.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(analysis_text)
        print(f"Analysis saved to '{filename}'")
        return True
    except Exception as e:
        print(f"ERROR: Error saving analysis file: {e}")
        return False


def save_workflow_files(mermaid_code, compiled_workflow, analysis_text=None, base_filename="workflow_diagram"):
    """
    Save .mmd, .png, and optionally .txt files with the same timestamp.
    
    Args:
        mermaid_code (str): The Mermaid diagram code
        compiled_workflow: The compiled LangGraph workflow
        analysis_text (str, optional): The analysis content to save
        base_filename (str): Base filename (without extension)
        
    Returns:
        tuple: (mmd_success, png_success, txt_success)
    """
    # Create diagrams folder if it doesn't exist
    os.makedirs("diagrams", exist_ok=True)
    
    # Generate single timestamp for all files
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    
    # Save .mmd file
    mmd_success = False
    try:
        mmd_filename = f"diagrams/{timestamp}-{base_filename}.mmd"
        with open(mmd_filename, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        print(f"Mermaid code saved to '{mmd_filename}'")
        mmd_success = True
    except Exception as e:
        print(f"ERROR: Error saving Mermaid file: {e}")
    
    # Save .png file
    png_success = False
    try:
        print("Generating PNG using Mermaid.ink API...")
        png_data = compiled_workflow.get_graph().draw_mermaid_png()
        png_filename = f"diagrams/{timestamp}-{base_filename}.png"
        
        with open(png_filename, "wb") as f:
            f.write(png_data)
        
        print(f"PNG saved as '{png_filename}'")
        png_success = True
        
    except Exception as e:
        print(f"ERROR: Error generating PNG: {e}")
        print("NOTE: This might be due to network issues or complex diagram structure")
    
    # Save .txt file (if analysis provided)
    txt_success = False
    if analysis_text:
        try:
            txt_filename = f"diagrams/{timestamp}-{base_filename}-analysis.txt"
            with open(txt_filename, 'w', encoding='utf-8') as f:
                f.write(analysis_text)
            print(f"Analysis saved to '{txt_filename}'")
            txt_success = True
        except Exception as e:
            print(f"ERROR: Error saving analysis file: {e}")
    else:
        txt_success = None  # Not requested
    
    return mmd_success, png_success, txt_success


def display_mermaid_instructions(mermaid_code):
    """
    Display instructions for using the Mermaid code.
    
    Args:
        mermaid_code (str): The generated Mermaid code
    """
    print("\n" + "=" * 80)
    print("MERMAID DIAGRAM CODE")
    print("=" * 80)
    print("Copy the code below and paste it into https://mermaid.live/ to visualize:")
    print("\n" + "-" * 40)
    print(mermaid_code)
    print("-" * 40)
    
    print("\nALTERNATIVE USAGE:")
    print("- Paste into GitHub README.md (supports Mermaid)")
    print("- Use in GitLab, Notion, or other platforms that support Mermaid")
    print("- Save as .mmd file and use with Mermaid CLI")


def analyze_workflow(compiled_workflow, return_string=False):
    """
    Analyze and display workflow statistics.
    
    Args:
        compiled_workflow: The compiled LangGraph workflow
        return_string (bool): If True, return analysis as string instead of printing

    Returns:
        str: Analysis text if return_string=True, None otherwise
    """
    try:
        graph = compiled_workflow.get_graph()
        
        analysis_lines = []
        analysis_lines.append("=" * 80)
        analysis_lines.append("WORKFLOW ANALYSIS")
        analysis_lines.append("=" * 80)
        
        nodes = list(graph.nodes.keys())
        edges = graph.edges
        
        analysis_lines.append(f"Total Nodes: {len(nodes)}")
        analysis_lines.append(f"Total Edges: {len(edges)}")
        
        analysis_lines.append(f"\nNode List:")
        for i, node_id in enumerate(nodes, 1):
            analysis_lines.append(f"  {i:2d}. {node_id}")
        
        analysis_lines.append(f"\nEdge List:")
        for i, edge in enumerate(edges, 1):
            edge_type = "conditional" if hasattr(edge, 'condition') else "direct"
            analysis_lines.append(f"  {i:2d}. {edge.source} -> {edge.target} ({edge_type})")
            
        # Look for cycles (retry loops)
        analysis_lines.append(f"\nPotential Retry Loops:")
        retry_edges = []
        for edge in edges:
            # Simple heuristic: if target appears earlier in node list than source
            try:
                source_idx = nodes.index(edge.source)
                target_idx = nodes.index(edge.target)
                if target_idx < source_idx:
                    retry_edges.append(f"{edge.source} -> {edge.target}")
            except ValueError:
                continue
        
        if retry_edges:
            for loop in retry_edges:
                analysis_lines.append(f"  - {loop}")
        else:
            analysis_lines.append("  - No obvious retry loops detected")
        
        analysis_text = "\n".join(analysis_lines)
        
        if return_string:
            print("\n" + analysis_text)  # Still print to console
            return analysis_text
        else:
            print("\n" + analysis_text)
            return None
            
    except Exception as e:
        error_msg = f"ERROR: Error analyzing workflow: {e}"
        if return_string:
            return error_msg
        else:
            print(error_msg)
            return None


def main():
    """
    Main function to run the visualization process.
    """
    print("LangGraph Workflow Visualizer")
    print("=" * 50)
    
    # Generate Mermaid visualization
    mermaid_code, success = generate_mermaid_visualization()
    
    if not success:
        print("ERROR: Failed to generate visualization. Check your workflow.py file.")
        return
    
    # Display the Mermaid code with instructions
    display_mermaid_instructions(mermaid_code)
    
    # Try to generate all files and analyze workflow
    try:
        compiled_workflow = build_workflow()
        
        # Get analysis as string (this will also print to console)
        analysis_text = analyze_workflow(compiled_workflow, return_string=True)
        
        # Save all files with the same timestamp
        mmd_success, png_success, txt_success = save_workflow_files(
            mermaid_code, 
            compiled_workflow, 
            analysis_text,
            "workflow_diagram"
        )
        
        print(f"\nFiles generated:")
        if mmd_success:
            print(f"  ✓ Mermaid file (.mmd)")
        if png_success:
            print(f"  ✓ PNG image (.png)")
        if txt_success:
            print(f"  ✓ Analysis file (.txt)")
        
    except Exception as e:
        print(f"ERROR: Error in file generation or analysis: {e}")
    
    print(f"\nVisualization complete!")
    print(f"Next steps:")
    print(f"  1. Open https://mermaid.live/")
    print(f"  2. Paste the Mermaid code from above")
    print(f"  3. Customize colors and styling as needed")
    print(f"  4. Check the 'diagrams' folder for saved files")


if __name__ == "__main__":
    main()