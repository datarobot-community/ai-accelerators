"""
Utility to create OpenAI-compatible LLM client for DataRobot LLM Gateway.
"""

import os
import json
import httpx

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from groq import Groq
except Exception:
    Groq = None

class LoggingTransport(httpx.HTTPTransport):
    def handle_request(self, request):
        print("=== RAW REQUEST BODY ===")
        # request.content contains the exact JSON sent over the wire
        try:
            print(json.dumps(json.loads(request.content), indent=2))
        except:
            print(request.content)
        print("========================\n")
        return super().handle_request(request)

def create_llm_client(model_name: str = None) -> tuple[OpenAI, str]:
    """
    Create an OpenAI-compatible client for DataRobot LLM Gateway or direct LLM using environment variables.
    
    Expects the following environment variables:
    - MODE: "dr-gateway" (use DataRobot LLM Gateway) or "direct-llm" (use deployed LLM directly)
    - DATAROBOT_ENDPOINT: DataRobot API endpoint URL (e.g., https://app.datarobot.com/api/v2) - required for dr-gateway mode
    - DATAROBOT_API_TOKEN: DataRobot API token for authentication - required for dr-gateway mode
    - LLM_ENDPOINT: URL of deployed LLM endpoint - required for direct-llm mode
    - LLM_API_KEY: API key for the deployed LLM endpoint - required for direct-llm mode
    - CHAT_COMPLETIONS_MODEL (optional): Default model name
    
    Args:
        model_name: Model name to use. If None, uses CHAT_COMPLETIONS_MODEL env var or defaults to "gpt-4o-mini".
    
    Returns:
        Tuple of (OpenAI client, model_name)
    
    Raises:
        RuntimeError: If required dependencies or environment variables are missing.
    """
    if OpenAI is None:
        raise RuntimeError("openai package is required. Please install dependencies from requirements.txt")
    
    # Get mode configuration (defaults to dr-gateway for backwards compatibility)
    mode = os.environ.get("MODE", "dr-gateway").lower()

    # Get timeout configuration
    default_timeout = 300
    timeout_seconds = int(os.environ.get("LLM_TIMEOUT", str(default_timeout)))
    
    # Resolve model name
    if model_name is None:
        model_name = os.environ.get("CHAT_COMPLETIONS_MODEL", "gpt-4o-mini")
    
    if mode == "direct-llm":
        # Direct LLM mode - use deployed LLM URL
        deployed_llm_url = os.environ.get("LLM_ENDPOINT")
        if not deployed_llm_url:
            raise RuntimeError("LLM_ENDPOINT environment variable is required for direct-llm mode")
        
        # For direct-llm, we might not need an API key or can use a different auth mechanism
        # Using a placeholder for now - adjust based on your deployed LLM's authentication
        api_key = os.environ.get("LLM_API_KEY", "not-needed")
        # transport = LoggingTransport()
        client = OpenAI(base_url=deployed_llm_url, 
                        api_key=api_key, 
                        timeout=timeout_seconds,
                        # http_client=httpx.Client(transport=transport)
                        )
        
    elif mode == "dr-gateway":
        # DataRobot LLM Gateway mode
        dr_endpoint = os.environ.get("DATAROBOT_ENDPOINT")
        dr_token = os.environ.get("DATAROBOT_API_TOKEN")
        
        if not dr_endpoint:
            raise RuntimeError("DATAROBOT_ENDPOINT environment variable is required for dr-gateway mode")
        if not dr_token:
            raise RuntimeError("DATAROBOT_API_TOKEN environment variable is required for dr-gateway mode")
        
        # Construct LLM Gateway URL
        llm_gateway_base_url = f"{dr_endpoint}/genai/llmgw"
        # transport = LoggingTransport()
        client = OpenAI(base_url=llm_gateway_base_url, 
                        api_key=dr_token, 
                        # http_client=httpx.Client(transport=transport)
                        )
        # client = Groq(api_key=dr_token)
        
    else:
        raise RuntimeError(f"Invalid MODE value: {mode}. Must be 'dr-gateway' or 'direct-llm'")
    
    return client, model_name
