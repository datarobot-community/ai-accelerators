## Developing custom tools

### Create a tool

Add your custom tools in `mcp_server/app/recipe/tools/`:

```python
# mcp_server/app/recipe/tools/my_custom_tool.py
from app.base.core.mcp_instance import mcp_server_tool
from app.base.core.common import get_sdk_client

@mcp_server_tool(tags={"custom", "recipe", "your-domain"})
async def my_custom_tool(input_param: str, optional_param: int = 10) -> str:
    """
    Brief description of what your tool does.
    
    This description helps LLMs understand when and how to use your tool.
    Be specific about the tool's purpose and behavior.
    
    Args:
        input_param: Description of the required parameter
        optional_param: Description of the optional parameter
        
    Returns:
        Description of what the tool returns
    """
    # Use the DataRobot SDK client for API operations
    client = get_sdk_client()
    
    # Example: List projects
    projects = client.Project.list()
    
    # Your custom logic here
    result = f"Processed {input_param} with {optional_param}"
    
    return result
```

### Tool best practices

- **📝 Clear Descriptions**: Provide detailed docstrings - LLMs use these to understand tool capabilities
- **🎯 Type Hints**: Always use type hints for parameters and return values
- **🔧 Error Handling**: Implement proper error handling and return meaningful error messages
- **⚡ Async/Await**: Tools should be async functions for better performance
- **🏷️ Tags**: Use descriptive tags to categorize tools (helps with tool filtering)
- **🔌 SDK Client**: Use `get_sdk_client()` for DataRobot API access

### Add custom resources

Resources provide static data or context to the AI agent:

```python
# mcp_server/app/recipe/resources/my_resource.py
from app.base.core.mcp_instance import mcp

@mcp.resource(uri="custom://my-data")
async def my_custom_resource() -> str:
    """Provide custom data or documentation to the agent."""
    return """
    # Custom Resource Data
    
    This resource provides context about...
    
    ## Available APIs
    - API 1: Description
    - API 2: Description
    """
```

### Add custom prompts

Prompt templates provide reusable instructions:

```python
# mcp_server/app/recipe/prompts/my_prompt.py
from app.base.core.mcp_instance import mcp

@mcp.prompt
async def my_custom_prompt(context: str) -> str:
    """Custom prompt template for specific tasks."""
    return f"""
    You are an expert assistant helping with {context}.
    
    Please follow these guidelines:
    1. Be specific and detailed
    2. Use the available tools effectively
    3. Provide clear explanations
    """
```

### Server lifecycle hooks

Customize server startup and shutdown behavior:

```python
# mcp_server/app/recipe/core/server_lifecycle.py
from app.base.core.mcp_server_server import ServerLifecycle

class RecipeServerLifecycle(ServerLifecycle):
    async def on_startup(self) -> None:
        """Called when server starts."""
        await super().on_startup()
        # Initialize connections, load data, etc.
        print("Custom startup logic executed")
        
    async def on_shutdown(self) -> None:
        """Called when server stops."""
        # Clean up resources, close connections, etc.
        print("Custom shutdown logic executed")
        await super().on_shutdown()
```