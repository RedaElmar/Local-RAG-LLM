#!/usr/bin/env python3
"""
Configuration Management Script for AI Research Assistant
Provides utilities to manage, validate, and update agent configurations
"""

import sys
import os
import yaml
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.config_loader import ConfigLoader, get_config

def validate_config():
    """Validate the current configuration and report any issues"""
    print("🔍 Validating configuration...")
    
    try:
        config = get_config()
        errors = config.validate_config()
        
        if not errors:
            print("✅ Configuration is valid!")
            return True
        else:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"   - {error}")
            return False
            
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False

def show_config_summary():
    """Show a summary of the current configuration"""
    print("📋 Configuration Summary")
    print("=" * 50)
    
    try:
        config = get_config()
        
        # Show agents
        print("\n🤖 Agents:")
        for agent_name in config.get_agent_names():
            agent_config = config.get_agent_config(agent_name)
            print(f"   - {agent_config['name']} ({agent_name})")
            print(f"     Role: {agent_config['role']}")
            print(f"     Description: {agent_config['description'][:60]}...")
        
        # Show pipeline
        print("\n🔄 Pipeline:")
        steps = config.get_pipeline_steps()
        total_time = sum(step.get('estimated_time', 2) for step in steps)
        print(f"   Total steps: {len(steps)}")
        print(f"   Estimated time: {total_time} seconds")
        
        for i, step in enumerate(steps, 1):
            print(f"   {i}. {step['name']} ({step['agent']}) - {step.get('estimated_time', 2)}s")
        
        # Show models
        print("\n🧠 Models:")
        for model_name in config.get_model_names():
            model_config = config.get_model_config(model_name)
            print(f"   - {model_config['name']} ({model_name})")
            print(f"     Provider: {model_config['provider']}")
            print(f"     Context: {model_config['context_length']} tokens")
        
        # Show output options
        print("\n📄 Output Options:")
        output_config = config.get_output_config()
        templates = config.get_report_templates()
        print(f"   Default template: {config.get_default_template()}")
        print(f"   Available templates: {', '.join(templates.keys())}")
        print(f"   Output formats: {', '.join(output_config.get('formats', []))}")
        
    except Exception as e:
        print(f"❌ Error showing configuration: {e}")

def reload_config():
    """Reload the configuration from file"""
    print("🔄 Reloading configuration...")
    
    try:
        config = get_config()
        config.reload_config()
        print("✅ Configuration reloaded successfully!")
        return True
    except Exception as e:
        print(f"❌ Error reloading configuration: {e}")
        return False

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "global": {
            "default_model": "gemma3:4b",
            "max_context_length": 4096,
            "temperature": 0.7,
            "max_tokens": 2048,
            "timeout_seconds": 30
        },
        "agents": {
            "decomposer": {
                "name": "Decomposer Agent",
                "role": "Research Question Analyzer",
                "description": "Breaks down complex research questions into structured sub-questions",
                "system_prompt": "You are a research question analyzer...",
                "parameters": {
                    "temperature": 0.6,
                    "max_tokens": 1024,
                    "top_p": 0.9
                }
            }
        },
        "pipeline": {
            "name": "Multi-Agent Research Pipeline",
            "description": "Sequential processing pipeline for comprehensive research analysis",
            "steps": [
                {
                    "name": "Query Decomposition",
                    "agent": "decomposer",
                    "description": "Break down research question into components",
                    "estimated_time": 2,
                    "required": True
                }
            ],
            "behavior": {
                "parallel_processing": False,
                "error_handling": "stop_on_error",
                "retry_attempts": 1,
                "progress_reporting": True,
                "intermediate_outputs": True
            }
        }
    }
    
    config_path = Path("config/sample_agents.yaml")
    config_path.parent.mkdir(exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as file:
        yaml.dump(sample_config, file, default_flow_style=False, indent=2, allow_unicode=True)
    
    print(f"✅ Sample configuration created at {config_path}")

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python manage_config.py <command>")
        print("\nAvailable commands:")
        print("  validate    - Validate the current configuration")
        print("  summary     - Show configuration summary")
        print("  reload      - Reload configuration from file")
        print("  sample      - Create a sample configuration file")
        print("  help        - Show this help message")
        return
    
    command = sys.argv[1].lower()
    
    if command == "validate":
        validate_config()
    elif command == "summary":
        show_config_summary()
    elif command == "reload":
        reload_config()
    elif command == "sample":
        create_sample_config()
    elif command == "help":
        print("Configuration Management Script for AI Research Assistant")
        print("\nThis script helps manage the YAML-based configuration system.")
        print("\nCommands:")
        print("  validate    - Check if the configuration file is valid")
        print("  summary     - Display a summary of all configuration options")
        print("  reload      - Reload configuration without restarting the server")
        print("  sample      - Create a sample configuration file for reference")
    else:
        print(f"Unknown command: {command}")
        print("Use 'python manage_config.py help' for available commands")

if __name__ == "__main__":
    main()
