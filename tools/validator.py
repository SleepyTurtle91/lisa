from typing import Dict, Any, List
from lisa.tools.base import BaseTool
from lisa.core.errors import ValidationError

RESERVED_KEYWORDS = {"eval", "exec", "system", "lisa_internal", "self", "import"}

class ToolValidator:
    @staticmethod
    def validate_tool(tool: BaseTool, registered_names: List[str]) -> None:
        name = tool.name.strip()
        if not name:
            raise ValidationError("Tool name cannot be empty.")
            
        if name in registered_names:
            raise ValidationError(f"Duplicate tool name: '{name}'.")
            
        if name in RESERVED_KEYWORDS:
            raise ValidationError(f"Tool name '{name}' uses reserved keyword.")
            
        schema = tool.parameters_schema
        if not isinstance(schema, dict):
            raise ValidationError(f"Tool '{name}' parameters_schema must be a dictionary.")
            
        schema_type = schema.get("type")
        if schema_type and schema_type != "object":
            raise ValidationError(f"Tool '{name}' top-level schema type must be 'object'.")
            
        properties = schema.get("properties")
        if properties is not None and not isinstance(properties, dict):
            raise ValidationError(f"Tool '{name}' properties must be a dictionary.")
            
        required = schema.get("required")
        if required is not None:
            if not isinstance(required, list):
                raise ValidationError(f"Tool '{name}' required field must be a list.")
            if properties is not None:
                for req_param in required:
                    if req_param not in properties:
                        raise ValidationError(
                            f"Tool '{name}' required property '{req_param}' is not defined in properties."
                        )
