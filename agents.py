# agents.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.callbacks import UsageMetadataCallbackHandler # token + cost tracking
from langchain_anthropic import ChatAnthropic  # Import Anthropic
#from langchain_google_genai import ChatGoogleGenerativeAI # Import Google Gemini
#from langchain_deepseek import ChatDeepSeek # Import DeepSeek AI
#from langchain_mistralai import ChatMistralAI  # Import Mistral AI
import os
import logging
from dotenv import load_dotenv

# Import the system prompts from prompts.py
from prompts import (
    REQUIREMENT_ELICITOR_PROMPT,
    SIMULATION_PLAN_PROMPT,
    CODE_GENERATOR_PROMPT,
    CODE_VALIDATOR_PROMPT,
    SCENARIO_TESTER_PROMPT
)

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

LEGACY_MODEL_ALIASES = {
    "claude-3-7-sonnet-latest": "claude-sonnet-4-6",
    "claude-3-5-sonnet-latest": "claude-sonnet-4-6",
    "claude-3-5-haiku-latest": "claude-haiku-4-5",
}


def _resolve_anthropic_model(model):
    """Normalize Anthropic model IDs and map retired aliases to current API IDs."""
    selected_model = model or DEFAULT_ANTHROPIC_MODEL
    resolved_model = LEGACY_MODEL_ALIASES.get(selected_model, selected_model)
    if resolved_model != selected_model:
        logger.warning(
            "Anthropic model '%s' is retired/unsupported; using '%s' instead.",
            selected_model,
            resolved_model,
        )
    return resolved_model


def get_llm(model=None, temperature=0.0, callbacks=None):
    """Initialize the LLM with given parameters."""
    if callbacks is None:
        callbacks = []
    selected_model = _resolve_anthropic_model(model)
        
    return ChatAnthropic(
        model=selected_model,
        temperature=temperature,
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        callbacks=callbacks
    )

def get_coding_llm(model=None, temperature=0.0, callbacks=None):
    """Get an LLM optimized for code generation tasks."""
    if callbacks is None:
        callbacks = []
    selected_model = _resolve_anthropic_model(model)
        
    return ChatAnthropic(
        model=selected_model,
        temperature=temperature,
        max_tokens=64000,
        timeout=None,
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        callbacks=callbacks
    )

def create_requirement_elicitor_agent(callbacks=None):
    """Create an agent for eliciting simulation requirements."""
    if callbacks is None:
        callbacks = []

    prompt = ChatPromptTemplate.from_messages([
        ("system", REQUIREMENT_ELICITOR_PROMPT),
        MessagesPlaceholder(variable_name="conversation_history")
    ])
    return prompt | get_llm(callbacks=callbacks) | StrOutputParser()

def create_simulation_plan_agent(callbacks=None):
    """Create an agent for generating a simulation plan."""
    if callbacks is None:
        callbacks = []
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SIMULATION_PLAN_PROMPT),
        ("user", "{requirements_summary}")
    ])
    return prompt | get_llm(callbacks=callbacks) | StrOutputParser()

def create_code_generator_agent(callbacks=None):
    """Create an agent for generating SimPy code."""
    if callbacks is None:
        callbacks = []

    prompt = ChatPromptTemplate.from_messages([
        ("system", CODE_GENERATOR_PROMPT),
        ("user", "{simulation_plan}")
    ])
    return prompt | get_coding_llm(callbacks=callbacks) | StrOutputParser()

def create_code_validator_agent(callbacks=None):
    """Create an agent for validating SimPy code."""
    if callbacks is None:
        callbacks = []
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", CODE_VALIDATOR_PROMPT),
        ("user", """Requirements:{requirements_summary}
         
Code:{generated_code}""")
    ])
    return prompt | get_coding_llm(callbacks=callbacks) | StrOutputParser()

def create_scenario_tester_agent(callbacks=None):
    """Create an agent for analyzing test results."""
    if callbacks is None:
        callbacks = []

    prompt = ChatPromptTemplate.from_messages([
        ("system", SCENARIO_TESTER_PROMPT),
        ("user", """Requirements Summary: {requirements_summary}

Test Results:
{test_results}""")
    ])
    return prompt | get_coding_llm(callbacks=callbacks) | StrOutputParser()