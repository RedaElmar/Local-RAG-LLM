# agents/decomposer.py

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

class DecomposerAgent:
    name = "Decomposer Agent"
    role = "Research Question Analyzer"
    
    @staticmethod
    def run(prompt, model):
        print(f"🤖 [DEBUG] DecomposerAgent.run() called")
        print(f"📝 [DEBUG] Prompt length: {len(prompt)} characters")
        print(f"🔧 [DEBUG] Model: {model}")
        
        try:
            # Get system prompt and parameters from YAML config
            print("⚙️ [DEBUG] Getting agent prompt and parameters...")
            system_prompt = get_agent_prompt('decomposer')
            parameters = get_agent_parameters('decomposer')
            print(f"✅ [DEBUG] System prompt length: {len(system_prompt)} characters")
            print(f"✅ [DEBUG] Parameters: {parameters}")
            
            print("🚀 [DEBUG] Calling generate() function...")
            result = generate(prompt, system_prompt=system_prompt, model=model, **parameters)
            print(f"✅ [DEBUG] Generate() completed successfully")
            print(f"📄 [DEBUG] Result length: {len(result)} characters")
            print(f"📄 [DEBUG] Result preview: {result[:100]}...")
            
            return result
            
        except Exception as e:
            print(f"❌ [DEBUG] DecomposerAgent.run() failed with error: {e}")
            print(f"🔍 [DEBUG] Error type: {type(e).__name__}")
            import traceback
            print(f"📋 [DEBUG] Full traceback:")
            traceback.print_exc()
            raise e
