"""
Tool registry and execution.

Tools are plain Python functions decorated with @register_tool.
They get auto-converted to OpenAI function-calling schema.
"""

import json
import inspect
from typing import Callable, Optional, get_type_hints


# Global tool registry
_TOOLS: dict[str, dict] = {}


def register_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    param_descriptions: Optional[dict] = None,
):
    """Decorator to register a function as an agent tool.

    When `param_descriptions` is provided, each `{param_name: text}` entry is
    attached to the generated JSON Schema property as `description`, so the
    LLM sees per-parameter semantics in the function-calling schema instead of
    just bare types.
    """
    pdesc = param_descriptions or {}

    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip().split("\n")[0]

        # Build parameter schema from type hints
        hints = get_type_hints(func)
        sig = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("workspace", "context"):
                continue  # injected at runtime
            param_type = hints.get(param_name, str)
            prop = _type_to_schema(param_type)
            if param_name in pdesc:
                prop["description"] = pdesc[param_name]
            properties[param_name] = prop
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_desc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

        _TOOLS[tool_name] = {
            "schema": schema,
            "func": func,
        }
        func._tool_name = tool_name
        return func

    return decorator


def get_tool_schemas(tool_names: Optional[list[str]] = None) -> list[dict]:
    """Get OpenAI-format tool schemas."""
    if tool_names is None:
        return [t["schema"] for t in _TOOLS.values()]
    return [_TOOLS[n]["schema"] for n in tool_names if n in _TOOLS]


def execute_tool(name: str, arguments: str, workspace: str, context: dict) -> str:
    """Execute a registered tool and return result as string."""
    if name not in _TOOLS:
        return f"Error: Unknown tool '{name}'"

    func = _TOOLS[name]["func"]
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        return f"Error: Invalid JSON arguments: {arguments}"

    # Inject workspace and context if the function accepts them
    sig = inspect.signature(func)
    if "workspace" in sig.parameters:
        args["workspace"] = workspace
    if "context" in sig.parameters:
        args["context"] = context

    try:
        result = func(**args)
        return result if isinstance(result, str) else json.dumps(result, indent=2)
    except Exception as e:
        return f"Error executing {name}: {type(e).__name__}: {str(e)}"


def _type_to_schema(python_type) -> dict:
    """Convert Python type hint to JSON Schema."""
    if python_type == str:
        return {"type": "string"}
    elif python_type == int:
        return {"type": "integer"}
    elif python_type == float:
        return {"type": "number"}
    elif python_type == bool:
        return {"type": "boolean"}
    elif python_type == Optional[str] or str(python_type) == "typing.Optional[str]":
        return {"type": "string"}
    else:
        return {"type": "string"}
