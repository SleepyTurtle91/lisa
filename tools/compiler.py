from typing import Any, Dict, Optional, List, Tuple
from lisa.tools.base import BaseTool

class ToolCompiler:
    _schema_cache: Dict[str, Dict[str, Any]] = {}
    _hits: int = 0
    _misses: int = 0

    @classmethod
    def compile_schema(cls, tool: BaseTool, provider_id: str) -> Dict[str, Any]:
        """Compiles and caches a tool's generic parameter schema into provider-specific format."""
        cache_key = f"{provider_id}:{tool.name}"
        if cache_key in cls._schema_cache:
            cls._hits += 1
            return cls._schema_cache[cache_key]

        cls._misses += 1
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
    def get_cache_stats(cls) -> Tuple[int, int]:
        """Returns (hits, misses)."""
        return cls._hits, cls._misses

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the compiled schema cache and resets counters."""
        cls._schema_cache.clear()
        cls._hits = 0
        cls._misses = 0

    @staticmethod
    def filter_tools(tools: List[BaseTool], intent_keywords: Optional[List[str]] = None) -> List[BaseTool]:
        """Filters available tools based on active session prompt keywords/permissions."""
        if not intent_keywords:
            return tools

        filtered: List[BaseTool] = []
        for tool in tools:
            name_desc = f"{tool.name} {tool.description}".lower()
            if any(kw.lower() in name_desc for kw in intent_keywords):
                filtered.append(tool)

        return filtered if filtered else tools
