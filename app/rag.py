import os
import argparse
from typing import List, Dict, Any
import time

try:
    from .ollama_client import generate
    from .indexer import build_index, retrieve
    from .agents.decomposer import DecomposerAgent
    from .agents.critique import CritiqueAgent
    from .agents.synthesis import SynthesisAgent
    from .agents.report_formatter import ReportFormatterAgent
    from .config_loader import get_pipeline_steps, get_agent_config, get_config
except ImportError:
    # Fallback for when running as standalone
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from ollama_client import generate
    from indexer import build_index, retrieve
    from agents.decomposer import DecomposerAgent
    from agents.critique import CritiqueAgent
    from agents.synthesis import SynthesisAgent
    from agents.report_formatter import ReportFormatterAgent
    from config_loader import get_pipeline_steps, get_agent_config, get_config

DOCS_DIR = os.getenv("DOCS_DIR", "data/docs")
INDEX_DIR = os.getenv("INDEX_DIR", "data/index")

def rebuild_index():
    """Rebuild the document index from scratch"""
    try:
        print("Rebuilding document index...")
        build_index()
        print("Index rebuilt successfully!")
        return {
            "success": True,
            "message": "Document index rebuilt successfully",
            "timestamp": os.path.getmtime(INDEX_DIR) if os.path.exists(INDEX_DIR) else None
        }
    except Exception as e:
        print(f"Error rebuilding index: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Agent mapping
AGENT_MAP = {
    "decomposer": DecomposerAgent,
    "critique": CritiqueAgent,
    "synthesis": SynthesisAgent,
    "report_formatter": ReportFormatterAgent,
}

def sources_to_markdown(sources):
    """Convert source list to markdown format"""
    if not sources:
        return "No sources available"
    
    md_sources = []
    for i, source in enumerate(sources, 1):
        if source and source != "Unknown":
            md_sources.append(f"{i}. **{source}**")
        else:
            md_sources.append(f"{i}. Unknown source")
    
    return "\n".join(md_sources)

def run_pipeline(query, model="gemma3:4b"):  # Default to Gemma 3 4B
    """Run the multi-agent pipeline for comprehensive research analysis"""
    print(f"🚀 [DEBUG] Starting multi-agent pipeline for query: {query[:50]}...")
    print(f"🔧 [DEBUG] Using model: {model}")
    
    try:
        # Get pipeline configuration from YAML
        print("📋 [DEBUG] Loading pipeline configuration...")
        config = get_config()
        pipeline_steps = config.get_pipeline_steps()
        print(f"✅ [DEBUG] Loaded {len(pipeline_steps)} pipeline steps")
        
        # Retrieve relevant context (reduced from 8 to 4 for performance)
        print("🔍 [DEBUG] Retrieving relevant context...")
        passages = retrieve(query, k=4)
        context = "\n".join(p.node.text for p in passages)
        sources = [p.metadata.get("source") for p in passages]
        sources_md = sources_to_markdown(sources)
        print(f"✅ [DEBUG] Retrieved {len(passages)} passages, {len(context)} characters")
        
        # Initialize context with query and retrieved information
        ctx = {
            "query": query, 
            "context": context, 
            "sources_md": sources_md
        }
        print("📝 [DEBUG] Context initialized")
        
        # Run the pipeline and collect intermediate results for debugging
        steps = []
        step_names = [step["name"] for step in pipeline_steps]
        print(f"🔄 [DEBUG] Pipeline steps: {step_names}")
        
        for i, step in enumerate(pipeline_steps):
            step_name = step["name"]
            agent_name = step["agent"]
            
            print(f"\n🔄 [DEBUG] Starting step {i+1}/{len(pipeline_steps)}: {step_name}")
            print(f"🤖 [DEBUG] Using agent: {agent_name}")
            
            try:
                # Get agent class and configuration
                print(f"⚙️ [DEBUG] Getting agent configuration for {agent_name}...")
                agent_cls = AGENT_MAP[agent_name]
                agent_config = config.get_agent_config(agent_name)
                print(f"✅ [DEBUG] Agent config loaded: {agent_config.get('name', 'Unknown')}")
                
                # Create prompt based on step configuration
                print(f"📝 [DEBUG] Creating prompt for {agent_name}...")
                if agent_name == "decomposer":
                    # Use truncated context for decomposer to avoid timeout
                    truncated_context = context[:2000] + "..." if len(context) > 2000 else context
                    prompt = f"## {step_name}\n\n{agent_config['description']}\n\n### User Query\n{query}\n\n### Relevant Context\n{truncated_context}\n\nPlease break down this research question into structured components."
                    output_key = "breakdown"
                elif agent_name == "critique":
                    # Use summary context for critique to reduce prompt size
                    context_summary = context[:1500] + "..." if len(context) > 1500 else context
                    prompt = f"## {step_name}\n\n{agent_config['description']}\n\n### Breakdown\n{ctx.get('breakdown', 'N/A')}\n\n### Context Summary\n{context_summary}\n\nPlease review and improve this research framework."
                    output_key = "critique"
                elif agent_name == "synthesis":
                    # Use even shorter context for synthesis as it has previous agent outputs
                    context_summary = context[:1000] + "..." if len(context) > 1000 else context
                    prompt = f"## {step_name}\n\n{agent_config['description']}\n\n### Breakdown\n{ctx.get('breakdown', 'N/A')}\n\n### Critique\n{ctx.get('critique', 'N/A')}\n\n### Context Summary\n{context_summary}\n\nPlease synthesize this information into a comprehensive analysis."
                    output_key = "synthesis"
                elif agent_name == "report_formatter":
                    # Use concise sources for final report
                    concise_sources = sources_md[:500] + "..." if len(sources_md) > 500 else sources_md
                    prompt = f"## {step_name}\n\n{agent_config['description']}\n\n**Topic:** {query}\n\n**Breakdown:** {ctx.get('breakdown', 'N/A')}\n\n**Critique:** {ctx.get('critique', 'N/A')}\n\n**Synthesis:** {ctx.get('synthesis', 'N/A')}\n\n**Sources:** {concise_sources}\n\nPlease create a comprehensive, professional report."
                    output_key = "final_report"
                else:
                    prompt = f"## {step_name}\n\n{agent_config['description']}\n\nPlease process the following information:\n{context}"
                    output_key = f"{agent_name}_output"
                
                print(f"📝 [DEBUG] Prompt created ({len(prompt)} characters)")
                print(f"🔑 [DEBUG] Output key: {output_key}")
                
                # Run the agent
                print(f"🚀 [DEBUG] Starting agent execution for {agent_name}...")
                start_time = time.time()
                
                output = agent_cls.run(prompt, model)
                
                execution_time = time.time() - start_time
                print(f"✅ [DEBUG] Agent {agent_name} completed in {execution_time:.2f} seconds")
                print(f"📄 [DEBUG] Output length: {len(output)} characters")
                print(f"📄 [DEBUG] Output preview: {output[:100]}...")
                
                ctx[output_key] = output
                
                # Add step info for debugging
                steps.append({
                    "name": step_name,
                    "output": output,
                    "markdown": True,
                    "step_number": i + 1,
                    "agent_name": agent_name,
                    "estimated_time": step.get("estimated_time", 2),
                    "description": step.get("description", ""),
                    "execution_time": execution_time
                })
                
                print(f"✅ [DEBUG] Step {step_name} completed successfully")
                
            except Exception as step_error:
                print(f"❌ [DEBUG] Step {step_name} failed with error: {step_error}")
                print(f"🔍 [DEBUG] Error type: {type(step_error).__name__}")
                import traceback
                print(f"📋 [DEBUG] Full traceback:")
                traceback.print_exc()
                
                # Re-raise to be caught by outer exception handler
                raise step_error
        
        print(f"\n🎉 [DEBUG] All pipeline steps completed successfully!")
        print(f"📊 [DEBUG] Total steps: {len(steps)}")
        
        # Return successful result
        return {
            "answer": ctx.get("final_report", "Pipeline completed but no final report generated"),
            "sources": sources,
            "debug_steps": steps,
            "pipeline_complete": True,
            "total_steps": len(steps),
            "execution_summary": {
                "total_time": sum(step.get("execution_time", 0) for step in steps),
                "steps_completed": len(steps),
                "model_used": model
            }
        }
        
    except Exception as e:
        print(f"❌ [DEBUG] Pipeline failed with error: {e}")
        print(f"🔍 [DEBUG] Error type: {type(e).__name__}")
        import traceback
        print(f"📋 [DEBUG] Full traceback:")
        traceback.print_exc()
        
        # If any step fails, return error info with fallback
        error_msg = f"Pipeline failed at step {len(steps) + 1}: {str(e)}"
        print(f"⚠️ [DEBUG] {error_msg}")
        
        # If we have some completed steps, try to provide a partial result
        if steps:
            print(f"🔄 [DEBUG] Attempting to generate partial result from {len(steps)} completed steps...")
            try:
                partial_context = f"Query: {query}\n\nContext: {context}\n\n"
                for step in steps:
                    partial_context += f"\n{step['name']}:\n{step['output']}\n"
                
                # Generate a simple summary
                fallback_prompt = f"Based on the following completed research steps, provide a summary of what was accomplished:\n\n{partial_context}"
                print(f"📝 [DEBUG] Generating fallback response...")
                fallback_response = generate(fallback_prompt, "You are a research assistant. Provide a clear summary of the completed research steps.", model)
                print(f"✅ [DEBUG] Fallback response generated ({len(fallback_response)} characters)")
                
                return {
                    "answer": f"⚠️ Pipeline partially completed. Here's what was accomplished:\n\n{fallback_response}",
                    "sources": sources,
                    "debug_steps": steps,
                    "pipeline_complete": False,
                    "partial_success": True,
                    "error": error_msg,
                    "total_steps": len(steps)
                }
            except Exception as fallback_error:
                print(f"❌ [DEBUG] Fallback generation also failed: {fallback_error}")
                pass
        
        # If all else fails, return basic error info
        return {
            "answer": f"❌ Pipeline failed completely: {error_msg}",
            "sources": sources,
            "debug_steps": [],
            "pipeline_complete": False,
            "partial_success": False,
            "error": error_msg,
            "total_steps": 0
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--query", type=str, help="Test query for the pipeline")
    parser.add_argument("--model", type=str, default="gemma3:4b", help="Model to use (default: gemma3:4b)")
    
    args = parser.parse_args()
    
    if args.build:
        print("Building document index...")
        build_index()
        print("Index built successfully!")
    
    if args.query:
        print(f"Testing pipeline with query: {args.query}")
        result = run_pipeline(args.query, args.model)
        print("Pipeline result:", result)