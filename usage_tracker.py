import os
import json
import logging
from datetime import datetime
from langchain_core.callbacks import UsageMetadataCallbackHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("token_usage.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("token_usage")

class AgentUsageTracker:
    """Track token and cost usage across different agents."""
    
    def __init__(self):
        self.usage_data = {}
        self.run_id = datetime.now().strftime("%Y%m%d%H%M%S")

        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Create save directory path relative to the script location
        # Ensure token_usage directory exists
        self.output_dir = os.path.join(script_dir, "token-usage")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created directory: {self.output_dir}")
        
    def get_callback_for_agent(self, agent_name):
        """Create a new callback handler for a specific agent."""
        callback = UsageMetadataCallbackHandler()
        # Store the reference to retrieve data later
        if agent_name not in self.usage_data:
            self.usage_data[agent_name] = []
        return callback
    
    def log_usage_from_callback(self, agent_name, callback, metadata=None):
        """Extract usage data from a callback and log it."""      
        if not callback or not callback.usage_metadata:
            logger.info(f"No usage data available for {agent_name}")
            return None
            
        # Get the usage data
        usage = callback.usage_metadata
        
        # Calculate costs using Claude pricing for all tracked models.
        total_cost = 0
        for model, model_usage in usage.items():
            # Claude pricing: $3 per 1M input tokens, $15 per 1M output tokens.
            # Reference: https://docs.anthropic.com/en/docs/about-claude/pricing
            if "claude" not in model.lower():
                logger.warning(
                    f"Model '{model}' is not Claude-branded; applying Claude pricing as project default."
                )

            input_cost = (model_usage.get('input_tokens', 0) / 1000000) * 3
            output_cost = (model_usage.get('output_tokens', 0) / 1000000) * 15
            model_cost = input_cost + output_cost
                
            total_cost += model_cost
            
        # Create an entry with usage stats
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "usage": usage,
            "estimated_cost": total_cost,
            "metadata": metadata or {}
        }
        
        # Add to our records
        self.usage_data[agent_name].append(entry)
        
        # Log the usage
        logger.info(f"Agent: {agent_name}, Usage: {json.dumps(usage)}, Cost: ${total_cost:.6f}")
        
        return entry
    
    def get_total_usage(self):
        """Calculate total usage and cost across all agents."""
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0
        
        for agent_name, entries in self.usage_data.items():
            for entry in entries:
                for model, model_usage in entry["usage"].items():
                    total_input_tokens += model_usage.get('input_tokens', 0)
                    total_output_tokens += model_usage.get('output_tokens', 0)
                total_cost += entry["estimated_cost"]
        
        return {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost": total_cost,
            "run_id": self.run_id
        }
    
    def save_usage_report(self, filename=None):
        """Save the usage data to a JSON file."""
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if filename is None:
            filename = f"{timestamp}_usage_report_{self.run_id}.json"

        # Create full path with directory
        filepath = os.path.join(self.output_dir, filename)
            
        report = {
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "agent_usage": self.usage_data,
            "totals": self.get_total_usage()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Usage report saved to {filepath}")
        
        return filepath

# Create a global instance of the tracker
usage_tracker = AgentUsageTracker()