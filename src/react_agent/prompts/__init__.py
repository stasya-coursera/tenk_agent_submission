"""Jinja2 template-based prompts for the react agent."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Get the directory containing the prompt templates
_PROMPTS_DIR = Path(__file__).parent

# Initialize Jinja2 environment
_jinja_env = Environment(
    loader=FileSystemLoader(_PROMPTS_DIR),
    trim_blocks=True,
    lstrip_blocks=True
)

# Load the agent system template
agent_system_template = _jinja_env.get_template("agent_system.j2")

