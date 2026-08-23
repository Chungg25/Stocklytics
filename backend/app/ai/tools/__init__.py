import inspect
import importlib
import pkgutil
from typing import Callable, Dict, Any, List

# Type alias for a tool function
ToolFunction = Callable[..., Any]

# Global registry
_TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

def tool(name: str, description: str, parameters: Dict[str, Any] = None):
    """
    Decorator to register a function as an LLM tool.
    """
    if parameters is None:
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }

    def decorator(func: ToolFunction):
        _TOOL_REGISTRY[func.__name__] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            },
            "callable": func
        }
        return func
    return decorator

def load_tools():
    """
    Dynamically loads all modules in the tools directory so their @tool decorators trigger.
    """
    import app.ai.tools as tools_pkg
    for _, module_name, _ in pkgutil.iter_modules(tools_pkg.__path__):
        importlib.import_module(f"app.ai.tools.{module_name}")

def get_available_tools() -> List[Dict[str, Any]]:
    """
    Returns the JSON schema of all registered tools to send to the LLM.
    """
    if not _TOOL_REGISTRY:
        load_tools()
    
    return [
        {"type": "function", "function": t["function"]}
        for t in _TOOL_REGISTRY.values()
    ]

def get_tool_callable(name: str) -> ToolFunction:
    """
    Gets the Python function for a given tool name.
    """
    for t in _TOOL_REGISTRY.values():
        if t["function"]["name"] == name:
            return t["callable"]
    raise ValueError(f"Tool {name} not found in registry.")

def execute_tool(name: str, **kwargs) -> Any:
    """
    Executes a tool by name with the given arguments.
    """
    func = get_tool_callable(name)
    sig = inspect.signature(func)
    
    if "status_callback" not in sig.parameters:
        kwargs.pop("status_callback", None)
        
    try:
        return func(**kwargs)
    except Exception as e:
        return {"error": str(e)}
