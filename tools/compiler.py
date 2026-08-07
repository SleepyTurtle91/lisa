from typing import Any, Dict, Optional
from lisa.tools.base import BaseTool

class ToolCompiler:
    @staticmethod
    def compile_schema(tool: BaseTool, provider_id: str) -> Dict[str, Any]:
        """Compiles a tool's generic parameter schema into provider-specific format."""
        if provider_id == "ollama" or provider_id == "openai":
            return {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema
                }
            }
        # Default fallback standard schema
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters_schema
        }
