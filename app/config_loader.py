"""
Configuration loader for AI Research Assistant
Loads agent configurations, pipeline settings, and model parameters from YAML files
"""

import yaml
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

class ConfigLoader:
    """Loads and manages configuration from YAML files"""
    
    def __init__(self, config_path: str = "config/agents.yaml"):
        # Try multiple possible paths for the config file
        possible_paths = [
            Path(config_path),  # Relative to current working directory
            Path(__file__).parent.parent / config_path,  # Relative to this file
            Path.cwd() / config_path,  # Relative to current working directory
            Path.home() / "Desktop" / "test llm" / config_path,  # Absolute fallback
        ]
        
        self.config_path = None
        for path in possible_paths:
            if path.exists():
                self.config_path = path
                break
        
        if not self.config_path:
            raise FileNotFoundError(f"Configuration file not found. Tried: {[str(p) for p in possible_paths]}")
        
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(self.config_path, 'r', encoding='utf-8') as file:
            try:
                config = yaml.safe_load(file)
                return config
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML configuration: {e}")
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent"""
        if 'agents' not in self.config:
            raise KeyError("No agents section found in configuration")
        
        if agent_name not in self.config['agents']:
            raise KeyError(f"Agent '{agent_name}' not found in configuration")
        
        return self.config['agents'][agent_name]
    
    def get_agent_prompt(self, agent_name: str) -> str:
        """Get the system prompt for a specific agent"""
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('system_prompt', '')
    
    def get_agent_parameters(self, agent_name: str) -> Dict[str, Any]:
        """Get the LLM parameters for a specific agent"""
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('parameters', {})
    
    def get_pipeline_steps(self) -> List[Dict[str, Any]]:
        """Get the pipeline configuration steps"""
        if 'pipeline' not in self.config:
            raise KeyError("No pipeline section found in configuration")
        
        return self.config['pipeline'].get('steps', [])
    
    def get_pipeline_behavior(self) -> Dict[str, Any]:
        """Get pipeline behavior settings"""
        if 'pipeline' not in self.config:
            raise KeyError("No pipeline section found in configuration")
        
        return self.config['pipeline'].get('behavior', {})
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model"""
        if 'models' not in self.config:
            raise KeyError("No models section found in configuration")
        
        if model_name not in self.config['models']:
            raise KeyError(f"Model '{model_name}' not found in configuration")
        
        return self.config['models'][model_name]
    
    def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration settings"""
        return self.config.get('global', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration settings"""
        return self.config.get('output', {})
    
    def get_report_templates(self) -> Dict[str, Any]:
        """Get available report templates"""
        output_config = self.get_output_config()
        return output_config.get('report_templates', {})
    
    def get_default_template(self) -> str:
        """Get the default report template"""
        output_config = self.get_output_config()
        return output_config.get('default_template', 'academic')
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        self.config = self._load_config()
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Check required sections
        required_sections = ['agents', 'pipeline', 'models']
        for section in required_sections:
            if section not in self.config:
                errors.append(f"Missing required section: {section}")
        
        # Check agents have required fields
        if 'agents' in self.config:
            for agent_name, agent_config in self.config['agents'].items():
                required_fields = ['name', 'role', 'system_prompt']
                for field in required_fields:
                    if field not in agent_config:
                        errors.append(f"Agent '{agent_name}' missing required field: {field}")
        
        # Check pipeline steps
        if 'pipeline' in self.config:
            steps = self.config['pipeline'].get('steps', [])
            for i, step in enumerate(steps):
                if 'agent' not in step:
                    errors.append(f"Pipeline step {i+1} missing 'agent' field")
                if 'name' not in step:
                    errors.append(f"Pipeline step {i+1} missing 'name' field")
        
        return errors
    
    def get_agent_names(self) -> List[str]:
        """Get list of all available agent names"""
        if 'agents' not in self.config:
            return []
        return list(self.config['agents'].keys())
    
    def get_model_names(self) -> List[str]:
        """Get list of all available model names"""
        if 'models' not in self.config:
            return []
        return list(self.config['models'].keys())
    
    def get_default_model(self) -> str:
        """Get the default model name"""
        global_config = self.get_global_config()
        return global_config.get('default_model', 'gemma3:4b')

# Global configuration instance
config_loader = ConfigLoader()

def get_config() -> ConfigLoader:
    """Get the global configuration loader instance"""
    return config_loader

def reload_config() -> None:
    """Reload the global configuration"""
    config_loader.reload_config()

def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Get configuration for a specific agent"""
    return config_loader.get_agent_config(agent_name)

def get_agent_prompt(agent_name: str) -> str:
    """Get the system prompt for a specific agent"""
    return config_loader.get_agent_prompt(agent_name)

def get_agent_parameters(agent_name: str) -> Dict[str, Any]:
    """Get the LLM parameters for a specific agent"""
    return config_loader.get_agent_parameters(agent_name)

def get_pipeline_steps() -> List[Dict[str, Any]]:
    """Get the pipeline configuration steps"""
    return config_loader.get_pipeline_steps()

def get_model_config(model_name: str) -> Dict[str, Any]:
    """Get configuration for a specific model"""
    return config_loader.get_model_config(model_name)
