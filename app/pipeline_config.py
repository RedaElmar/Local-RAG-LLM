# pipeline_config.py

try:
    from .config_loader import get_pipeline_steps, get_agent_config
except ImportError:
    # Fallback for when running as standalone
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from config_loader import get_pipeline_steps, get_agent_config

def get_pipeline_config():
    """Get the pipeline configuration from YAML"""
    return get_pipeline_steps()

def get_pipeline_prompts():
    """Get formatted prompts for the pipeline steps"""
    steps = get_pipeline_steps()
    prompts = []
    
    for step in steps:
        agent_name = step['agent']
        agent_config = get_agent_config(agent_name)
        
        # Create prompt template based on agent role
        if agent_name == 'decomposer':
            prompt_template = f"## {step['name']}\n\n{agent_config['description']}\n\n### User Query\n{{query}}\n\n### Context\n{{context}}\n\nPlease break down this research question into structured components."
            inputs = ["query", "context"]
            output_key = "breakdown"
            
        elif agent_name == 'critique':
            prompt_template = f"## {step['name']}\n\n{agent_config['description']}\n\n### Breakdown\n{{breakdown}}\n\n### Context\n{{context}}\n\nPlease review and improve this research framework."
            inputs = ["breakdown", "context"]
            output_key = "critique"
            
        elif agent_name == 'synthesis':
            prompt_template = f"## {step['name']}\n\n{agent_config['description']}\n\n### Breakdown\n{{breakdown}}\n\n### Critique\n{{critique}}\n\n### Context\n{{context}}\n\nPlease synthesize this information into a comprehensive analysis."
            inputs = ["breakdown", "critique", "context"]
            output_key = "synthesis"
            
        elif agent_name == 'report_formatter':
            prompt_template = f"## {step['name']}\n\n{agent_config['description']}\n\n**Topic:** {{query}}\n\n**Breakdown:** {{breakdown}}\n\n**Critique:** {{critique}}\n\n**Synthesis:** {{synthesis}}\n\n**Sources:** {{sources_md}}\n\nPlease create a comprehensive, professional report."
            inputs = ["query", "breakdown", "critique", "synthesis", "sources_md"]
            output_key = "final_report"
            
        else:
            # Default fallback
            prompt_template = f"## {step['name']}\n\n{agent_config['description']}\n\nPlease process the following information:\n{{context}}"
            inputs = ["context"]
            output_key = f"{agent_name}_output"
        
        prompts.append({
            "name": step['name'],
            "agent": step['agent'],
            "prompt_template": prompt_template,
            "inputs": inputs,
            "output_key": output_key,
            "description": step.get('description', ''),
            "estimated_time": step.get('estimated_time', 2),
            "required": step.get('required', True),
            "depends_on": step.get('depends_on', [])
        })
    
    return prompts

# Legacy support - keep the old PIPELINE for backward compatibility
PIPELINE = get_pipeline_prompts()
