import requests, os
import time

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


def generate(prompt: str, system_prompt: str = "", model: str = "gemma3:4b", **kwargs) -> str:
    """Call the local Ollama REST API and return the model's reply."""
    print(f"🚀 [DEBUG] Ollama generate() called")
    print(f"🔧 [DEBUG] Model: {model}")
    print(f"📝 [DEBUG] Prompt length: {len(prompt)} characters")
    print(f"📝 [DEBUG] System prompt length: {len(system_prompt)} characters")
    print(f"⚙️ [DEBUG] Additional kwargs: {kwargs}")
    
    # Build the request payload with all parameters
    payload = {
        "model": model, 
        "prompt": f"{system_prompt}\n{prompt}", 
        "stream": False,
        # Performance optimization parameters with better defaults
        "num_predict": kwargs.get("num_predict", kwargs.get("max_tokens", 512)),  # Use provided or reasonable default
        "top_k": kwargs.get("top_k", 40),  # Balanced sampling
        "top_p": kwargs.get("top_p", 0.9),  # Standard top_p sampling
        "temperature": kwargs.get("temperature", 0.7),  # Balanced temperature
        "repeat_penalty": kwargs.get("repeat_penalty", 1.1),  # Standard repeat penalty
        "num_ctx": kwargs.get("num_ctx", 2048),  # Standard context window
        "stop": kwargs.get("stop", ["\n\n\n"]),  # Minimal stop tokens
    }
    
    # Override with any explicitly provided parameters (this ensures user parameters take precedence)
    for key, value in kwargs.items():
        if value is not None and key not in ["max_tokens"]:  # Skip max_tokens as it's handled by num_predict
            payload[key] = value
    
    print(f"📤 [DEBUG] Request payload: {payload}")
    print(f"🌐 [DEBUG] Ollama URL: {OLLAMA_URL}")
    
    try:
        # Use reasonable timeout defaults
        timeout = kwargs.get("timeout", 120)  # Default 2 minutes
        print(f"⏱️ [DEBUG] Request timeout: {timeout} seconds")
        
        print(f"📡 [DEBUG] Sending POST request to Ollama...")
        start_time = time.time()
        
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=timeout,
        )
        
        request_time = time.time() - start_time
        print(f"✅ [DEBUG] Ollama response received in {request_time:.2f} seconds")
        print(f"📊 [DEBUG] Response status: {resp.status_code}")
        
        resp.raise_for_status()
        
        response_data = resp.json()
        result = response_data["response"]
        
        print(f"✅ [DEBUG] Response parsed successfully")
        print(f"📄 [DEBUG] Response length: {len(result)} characters")
        print(f"📄 [DEBUG] Response preview: {result[:100]}...")
        
        return result
        
    except requests.exceptions.Timeout:
        error_msg = f"Ollama request timed out after {timeout} seconds. Model: {model}"
        print(f"❌ [DEBUG] {error_msg}")
        raise Exception(error_msg)
    except requests.exceptions.ConnectionError:
        error_msg = f"Could not connect to Ollama server at {OLLAMA_URL}"
        print(f"❌ [DEBUG] {error_msg}")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Ollama request failed: {str(e)}"
        print(f"❌ [DEBUG] {error_msg}")
        print(f"🔍 [DEBUG] Error type: {type(e).__name__}")
        import traceback
        print(f"📋 [DEBUG] Full traceback:")
        traceback.print_exc()
        raise Exception(error_msg)