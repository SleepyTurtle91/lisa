import uuid
from typing import List, Dict, Any
from lisa.core.runtime import BaseSession
from lisa.core.context import SessionContext
from lisa.core.states import SessionState
from lisa.core.errors import SessionError
from lisa.engine.inference import InferenceEngine
from lisa.engine.models import InferenceRequest
from lisa.tools.registry import ToolRegistry
from lisa.tools.compiler import ToolCompiler
from lisa.tools.dispatcher import ToolExecutor
from lisa.tools.base import ToolRequest

class LisaSession(BaseSession):
    def __init__(self, context: SessionContext, engine: InferenceEngine, registry: ToolRegistry):
        self._session_id = str(uuid.uuid4())
        self._context = context
        self._engine = engine
        self._registry = registry
        self._executor = ToolExecutor(registry, max_retries=1)
        self._history: List[Dict[str, Any]] = []
        self._state = SessionState.CREATED

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def state(self) -> SessionState:
        return self._state

    async def send_message(self, message: str) -> str:
        if self._state == SessionState.CLOSED or self._state == SessionState.FAILED:
            raise SessionError(f"Cannot send message on session in {self._state.name} state.")

        self._state = SessionState.RUNNING
        self._history.append({"role": "user", "content": message})
        
        try:
            while True:
                compiled_tools = [
                    ToolCompiler.compile_schema(t, self._context.provider_id or "ollama")
                    for t in self._registry.list_tools()
                ]
                
                inf_req = InferenceRequest(
                    session_id=self._session_id,
                    messages=self._history,
                    model_name=self._context.model_name,
                    requested_capabilities=self._context.capabilities,
                    tools=compiled_tools if compiled_tools else None
                )
                
                inf_result = await self._engine.execute(inf_req, preferred_provider_id=self._context.provider_id)
                if not inf_result.success or not inf_result.response:
                    raise SessionError(f"Inference Engine failed: {inf_result.error}")
                
                response = inf_result.response
                
                # If provider returned tool calls, execute each via ToolExecutor and append to history for re-inference
                if response.tool_calls:
                    for call in response.tool_calls:
                        func = call.get("function", {})
                        tool_name = func.get("name")
                        args = func.get("arguments", {})
                        tool_req = ToolRequest(tool_name=tool_name, arguments=args, session_id=self._session_id)
                        result = await self._executor.execute_request(tool_req)
                        self._history.append({
                            "role": "tool",
                            "content": str(result.output if result.success else result.error)
                        })
                    # Re-loop to send updated history containing tool results back to the model
                    continue
                
                # If no tool calls, model provided final text content
                self._history.append({"role": "assistant", "content": response.content})
                self._state = SessionState.READY
                return response.content
        except Exception as e:
            self._state = SessionState.FAILED
            raise SessionError(f"Session execution failed: {str(e)}") from e

    def close(self) -> None:
        self._state = SessionState.CLOSED
