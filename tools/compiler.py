from typing import Any, Dict, Optional, List
from lisa.tools.base import BaseTool

class ToolCompiler:
    _schema_cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def compile_schema(cls, tool: BaseTool, provider_id: str) -> Dict[str, Any]:
        """Compiles and caches a tool's generic parameter schema into provider-specific format."""
        cache_key = f"{provider_id}:{tool.name}"
        if cache_key in cls._schema_cache:
            return cls._schema_cache[cache_key]

        if provider_id in ("ollama", "openai"):
            compiled = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema
                }
            }
        else:
            compiled = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema
            }

        cls._schema_cache[cache_key] = compiled
        return compiled

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the compiled schema cache."""
        cls._schema_cache.clear()

    @staticmethod
    def filter_tools(tools: List[BaseTool], intent_keywords: Optional[List[str]] = None) -> List[BaseTool]:
        """Filters available tools based on active session prompt keywords/permissions."""
        if not intent_keywords:
            return tools

        filtered: List[BaseTool] = []
        for tool in tools:
            # Check if any keyword matches tool name or description
            name_desc = f"{tool.name} {tool.description}".lower()
            if any(kw.lower() in name_desc for kw in intent_keywords):
                filtered.append(tool)

        return filtered if filtered else tools
