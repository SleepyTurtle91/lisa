import time
import uuid
from typing import List, Dict, Any, Optional
from lisa.core.runtime import BaseSession
from lisa.core.context import SessionContext
from lisa.core.states import SessionState
from lisa.core.errors import SessionError
from lisa.engine.inference import InferenceEngine
from lisa.engine.models import InferenceRequest, InferenceResult, SessionTelemetry, ExecutionTelemetry
from lisa.tools.registry import ToolRegistry
from lisa.tools.compiler import ToolCompiler
from lisa.tools.dispatcher import ToolExecutor
from lisa.tools.base import ToolRequest
from lisa.telemetry.flight_recorder import FlightRecorder

class LisaSession(BaseSession):
    def __init__(self, context: SessionContext, engine: InferenceEngine, registry: ToolRegistry, flight_recorder: Optional[FlightRecorder] = None):
        self._session_id = str(uuid.uuid4())
        self._context = context
        self._engine = engine
        self._registry = registry
        self._flight_recorder = flight_recorder
        self._executor = ToolExecutor(registry, max_retries=1)
        self._history: List[Dict[str, Any]] = []
        self._state = SessionState.CREATED
        self._last_result: Optional[InferenceResult] = None
        
        # Cumulative Session Telemetry & Latency Breakdown
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_tokens = 0
        self._total_tool_calls = 0
        self._total_turns = 0
        self._provider_inference_ms = 0.0
        self._tool_execution_ms = 0.0
        self._total_latency_ms = 0.0

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def last_result(self) -> Optional[InferenceResult]:
        return self._last_result

    @property
    def session_telemetry(self) -> SessionTelemetry:
        hits, misses = ToolCompiler.get_cache_stats()
        return SessionTelemetry(
            total_prompt_tokens=self._total_prompt_tokens,
            total_completion_tokens=self._total_completion_tokens,
            total_tokens=self._total_tokens,
            total_tool_calls=self._total_tool_calls,
            total_turns=self._total_turns,
            boot_latency_ms=0.0,
            provider_inference_ms=self._provider_inference_ms,
            tool_execution_ms=self._tool_execution_ms,
            total_latency_ms=self._total_latency_ms,
            cache_hits=hits,
            cache_misses=misses
        )

    def _record_stage(self, stage: str, payload: Optional[Dict[str, Any]] = None) -> None:
        if self._flight_recorder is None:
            return
        event_payload = {"stage": stage, "session_id": self._session_id}
        if payload:
            event_payload.update(payload)
        self._flight_recorder.record_event("flight_stage", event_payload)

    async def send_message(self, message: str) -> str:
        if self._state == SessionState.CLOSED or self._state == SessionState.FAILED:
            raise SessionError(f"Cannot send message on session in {self._state.name} state.")

        self._state = SessionState.RUNNING
        self._record_stage("task_received", {"message": message})
        self._record_stage("project_context", {"project_path": str(self._context.project_path)})
        self._record_stage("objective_received", {"message": message, "project_path": str(self._context.project_path)})
        self._record_stage("target_discovery", {"message": message})
        self._record_stage("task_analysis", {"message": message})
        self._record_stage("model_selection", {"message": message})
        self._record_stage("scaffolding_decision", {"message": message})
        self._history.append({"role": "user", "content": message})
        session_start = time.perf_counter()
        
        try:
            while True:
                self._total_turns += 1
                
                # 1. Dynamic Tool Filtering based on prompt keywords
                keywords = message.split()
                all_tools = self._registry.list_tools()
                filtered_tools = ToolCompiler.filter_tools(all_tools, intent_keywords=keywords)

                # 2. Schema Compilation via ToolCompiler Cache
                compiled_tools = [
                    ToolCompiler.compile_schema(t, self._context.provider_id or "ollama")
                    for t in filtered_tools
                ]
                
                inf_req = InferenceRequest(
                    session_id=self._session_id,
                    messages=self._history,
                    model_name=self._context.model_name,
                    requested_capabilities=self._context.capabilities,
                    tools=compiled_tools if compiled_tools else None
                )
                
                inf_start = time.perf_counter()
                inf_result = await self._engine.execute(inf_req, preferred_provider_id=self._context.provider_id)
                inf_duration = (time.perf_counter() - inf_start) * 1000.0
                self._provider_inference_ms += inf_duration
                self._last_result = inf_result

                if not inf_result.success or not inf_result.response:
                    raise SessionError(f"Inference Engine failed: {inf_result.error}")
                
                # Accumulate Token Telemetry
                if inf_result.telemetry:
                    tel = inf_result.telemetry
                    self._total_prompt_tokens += tel.prompt_tokens
                    self._total_completion_tokens += tel.completion_tokens
                    self._total_tokens += tel.total_tokens

                response = inf_result.response
                self._record_stage("model_response", {"has_tool_calls": bool(response.tool_calls)})
                
                # 3. Execute tool calls if returned by model
                if response.tool_calls:
                    for call in response.tool_calls:
                        self._total_tool_calls += 1
                        func = call.get("function", {})
                        tool_name = func.get("name")
                        args = func.get("arguments", {})
                        self._record_stage("tool_request", {"tool_name": tool_name, "arguments": args})
                        self._record_stage("tool_call", {"tool_name": tool_name, "arguments": args})
                        tool_start = time.perf_counter()
                        tool_req_args = dict(args)
                        tool_req_args["user_prompt"] = message
                        tool_req = ToolRequest(tool_name=tool_name, arguments=tool_req_args, session_id=self._session_id)
                        result = await self._executor.execute_request(tool_req, project_path=self._context.project_path)
                        self._tool_execution_ms += (time.perf_counter() - tool_start) * 1000.0
                        if result.metadata:
                            resolution_payload = {
                                "tool_name": tool_name,
                                "input_path": result.metadata.get("input_path"),
                                "resolved_path": result.metadata.get("resolved_path"),
                                "path_kind": result.metadata.get("path_kind")
                            }
                            self._record_stage("path_resolution", resolution_payload)
                            if result.metadata.get("resolved_path") is not None:
                                self._record_stage("resolved_path", {
                                    "tool_name": tool_name,
                                    "resolved_path": result.metadata.get("resolved_path")
                                })
                        self._record_stage("tool_result", {"tool_name": tool_name, "success": result.success})
                        if not result.success:
                            self._record_stage("guarding_decision", {
                                "tool_name": tool_name,
                                "reason": result.error,
                            })
                            self._record_stage("blocked", {
                                "reason": result.error,
                                "tool_name": tool_name,
                            })
                        
                        self._history.append({
                            "role": "tool",
                            "content": str(result.output if result.success else result.error)
                        })
                    # Re-loop to send updated history back to model
                    continue
                
                # Final answer
                self._history.append({"role": "assistant", "content": response.content})
                self._record_stage("model_response", {"content": response.content})
                self._record_stage("final_conclusion", {"content": response.content})
                self._total_latency_ms = (time.perf_counter() - session_start) * 1000.0
                self._state = SessionState.READY
                return response.content
        except Exception as e:
            self._state = SessionState.FAILED
            self._total_latency_ms = (time.perf_counter() - session_start) * 1000.0
            self._record_stage("blocked", {"reason": str(e)})
            raise SessionError(f"Session execution failed: {str(e)}") from e

    def close(self) -> None:
        self._state = SessionState.CLOSED
