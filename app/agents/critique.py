# agents/critique.py

try:
    from ..ollama_client import generate
    from ..config_loader import get_agent_prompt, get_agent_parameters
except ImportError:
    # Fallback for when running as standalone
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from ollama_client import generate
    from config_loader import get_agent_prompt, get_agent_parameters

class CritiqueAgent:
    name = "Critique Agent"
    role = "Research Framework Reviewer"
    
    @staticmethod
    def run(prompt, model):
        # Get system prompt and parameters from YAML config
        system_prompt = get_agent_prompt('critique')
        parameters = get_agent_parameters('critique')
        
        return generate(prompt, system_prompt=system_prompt, model=model, **parameters)
