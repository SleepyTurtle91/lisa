from collections import deque
from typing import Any, Deque, Dict, List, Optional, TextIO
import sys


class FlightConsole:
    """Live console activity projection driven by real flight-recorder events."""

    VALID_MODES = {"off", "compact", "verbose"}

    def __init__(self, project_name: str, mode: str = "compact", stream: Optional[TextIO] = None, history_size: int = 8):
        self.project_name = project_name
        self.mode = mode if mode in self.VALID_MODES else "compact"
        self.stream = stream or sys.stdout
        self.history: Deque[str] = deque(maxlen=max(4, history_size))
        self.current_tool: Optional[str] = None
        self.current_target: Optional[str] = None
        self.current_model: Optional[str] = None
        self.current_provider: Optional[str] = None
        self.current_state: str = "idle"
        self.semantic_state: str = "UNKNOWN"
        self.semantic_reason: str = "insufficient evidence"
        self.model_response_class: str = "EMPTY"
        self.event_count = 0
        self._flight_open = False

        self._has_blocked_stage = False
        self._has_guarding_stage = False
        self._has_tool_call_stage = False
        self._tool_result_total = 0
        self._tool_result_any_failure = False
        self._tool_result_any_success = False
        self._has_model_request = False
        self._has_model_response = False
        self._has_final_conclusion = False
        self._last_model_response_text = ""
        self._blocked_reasons: List[str] = []

    def bind(self, recorder: Any) -> None:
        recorder.subscribe(self.handle_event)

    def set_mode(self, mode: str) -> bool:
        if mode not in self.VALID_MODES:
            return False
        self.mode = mode
        return True

    def handle_event(self, event_record: Dict[str, Any]) -> None:
        if self.mode == "off":
            return

        self.event_count += 1
        event_type = event_record.get("event_type", "")
        payload = event_record.get("payload") or {}

        self._ingest_event(event_type, payload)
        self.semantic_state, self.semantic_reason, self.model_response_class = self._classify_operator_state()

        messages = self._messages_for_event(event_type, payload)
        if not messages:
            return

        for msg in messages:
            self.history.append(msg)

        if self.mode == "compact":
            for msg in messages:
                self._emit(msg)
            return

        self._emit_verbose_block()

    def _messages_for_event(self, event_type: str, payload: Dict[str, Any]) -> List[str]:
        if event_type == "model_request":
            self.current_model = payload.get("model_name") or "unknown"
            self.current_provider = payload.get("provider_id") or "unknown"
            self.current_state = "thinking"
            return [
                "🧠 Thinking",
                f"   {self.current_model}",
                "⏳ Waiting",
                f"   Provider response ({self.current_provider})",
            ]

        if event_type == "model_response":
            tool_calls = payload.get("tool_calls")
            if tool_calls:
                self.current_state = "planning"
                return ["🎯 Planning", "   Next action selected"]

            if self.semantic_state == "BLOCKED":
                self.current_state = "blocked"
                reason = self._blocked_reasons[-1] if self._blocked_reasons else "Blocked by runtime evidence"
                return ["⚠️ Blocked", f"   {reason}"]
            if self.semantic_state == "GUARDING":
                self.current_state = "guarding"
                if self.model_response_class == "ABSTENTION":
                    return ["🛡️ Guarding", "   Evidence threshold not met"]
                return [
                    "🛡️ Guarding",
                    "   Refusal or capability boundary",
                ]
            if self.semantic_state == "CLARIFYING":
                self.current_state = "clarifying"
                return ["❓ Clarifying", "   Additional information requested"]
            if self.semantic_state == "ERROR":
                self.current_state = "blocked"
                return ["⚠️ Blocked", "   Error evidence detected"]

            self.current_state = "completed"
            return ["✅ Completed", "   Response ready"]

        if event_type != "flight_stage":
            return []

        stage = payload.get("stage")
        if stage == "task_received":
            self.current_state = "orienting"
            return ["🦮 L.I.S.A. ACTIVE", "🧭 Orienting", "   Understanding objective"]
        if stage == "project_context":
            self.current_state = "orienting"
            project_path = payload.get("project_path")
            if project_path:
                return ["🧭 Orienting", f"   Project: {project_path}"]
            return ["🧭 Orienting", "   Loading project context"]
        if stage == "target_discovery":
            self.current_state = "looking"
            return ["👁 Looking", "   Discovering relevant targets"]
        if stage == "task_analysis":
            self.current_state = "planning"
            return ["🎯 Planning", "   Analyzing constraints"]
        if stage == "model_selection":
            self.current_state = "planning"
            return ["🎯 Planning", "   Selecting model strategy"]
        if stage == "scaffolding_decision":
            self.current_state = "planning"
            return ["🎯 Planning", "   Selecting scaffolding level"]
        if stage == "tool_request":
            tool_name = payload.get("tool_name") or "unknown_tool"
            arguments = payload.get("arguments") or {}
            target = self._extract_target(arguments)
            self.current_tool = tool_name
            self.current_target = target
            self.current_state = "using"

            if target:
                return [
                    "🔧 Using",
                    f"   {tool_name}",
                    f"   └─ {target}",
                    "⏳ Waiting",
                    "   Tool result",
                ]
            return [
                "🔧 Using",
                f"   {tool_name}",
                "⏳ Waiting",
                "   Tool result",
            ]
        if stage == "path_resolution":
            self.current_state = "looking"
            resolved = payload.get("resolved_path")
            if resolved:
                return ["👁 Looking", f"   {resolved}"]
            return []
        if stage == "guarding_decision":
            self.current_state = "guarding"
            reason = payload.get("reason")
            if reason:
                return ["🛡️ Guarding", "   Decision boundary applied", f"   {reason}"]
            return ["🛡️ Guarding", "   Decision boundary applied"]
        if stage == "tool_result":
            success = payload.get("success")
            tool_name = payload.get("tool_name") or self.current_tool or "tool"
            if success:
                self.current_state = "using"
                return ["✅ Tool result received", f"   {tool_name}"]
            self.current_state = "blocked"
            return ["⚠️ Blocked", f"   Tool failed: {tool_name}"]
        if stage == "blocked":
            self.current_state = "blocked"
            reason = payload.get("reason")
            if reason:
                return ["⚠️ Blocked", f"   {reason}"]
            return ["⚠️ Blocked", "   Runtime cannot proceed safely"]
        if stage == "final_conclusion":
            terminal = "✅ Completed"
            terminal_detail = "   Flight finished"
            if self.semantic_state == "BLOCKED":
                self.current_state = "blocked"
                terminal = "⚠️ Blocked"
                terminal_detail = "   Flight finished with blocked state"
            elif self.semantic_state == "GUARDING":
                self.current_state = "guarding"
                terminal = "🛡️ Guarding"
                terminal_detail = "   Flight finished with guard decision"
            elif self.semantic_state == "CLARIFYING":
                self.current_state = "clarifying"
                terminal = "❓ Clarifying"
                terminal_detail = "   Flight finished awaiting clarification"
            else:
                self.current_state = "completed"
            return ["📼 Recording", f"   Flight event #{self.event_count}", terminal, terminal_detail]

        return []

    def _extract_target(self, arguments: Dict[str, Any]) -> Optional[str]:
        for key in ("path", "file", "target", "directory", "url", "command"):
            value = arguments.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _ingest_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == "model_request":
            if not self._flight_open:
                self._reset_flight_evidence()
                self._flight_open = True
            self._has_model_request = True
            return

        if event_type == "model_response":
            self._has_model_response = True
            content = payload.get("content")
            if isinstance(content, str):
                self._last_model_response_text = content
            return

        if event_type != "flight_stage":
            return

        stage = payload.get("stage")
        if stage in {"task_received", "tool_request"} and not self._flight_open:
            self._reset_flight_evidence()
            self._flight_open = True
        if stage == "tool_call":
            self._has_tool_call_stage = True
        elif stage == "tool_result":
            self._tool_result_total += 1
            success = payload.get("success")
            if success is True:
                self._tool_result_any_success = True
            if success is False:
                self._tool_result_any_failure = True
        elif stage == "guarding_decision":
            self._has_guarding_stage = True
        elif stage == "blocked":
            self._has_blocked_stage = True
            reason = payload.get("reason")
            if isinstance(reason, str) and reason:
                self._blocked_reasons.append(reason)
        elif stage == "final_conclusion":
            self._has_final_conclusion = True
            self._flight_open = False

    def _reset_flight_evidence(self) -> None:
        self.semantic_state = "UNKNOWN"
        self.semantic_reason = "insufficient evidence"
        self.model_response_class = "EMPTY"
        self._has_blocked_stage = False
        self._has_guarding_stage = False
        self._has_tool_call_stage = False
        self._tool_result_total = 0
        self._tool_result_any_failure = False
        self._tool_result_any_success = False
        self._has_model_request = False
        self._has_model_response = False
        self._has_final_conclusion = False
        self._last_model_response_text = ""
        self._blocked_reasons = []

    def _classify_model_response_text(self, text: str) -> str:
        lower = (text or "").strip().lower()
        if not lower:
            return "EMPTY"

        refusal_tokens = [
            "cannot",
            "can't",
            "not able",
            "unable",
            "do not have",
            "don't have",
            "no appropriate tool",
            "not supported",
            "not a standard operation",
        ]
        abstain_tokens = [
            "not enough evidence",
            "need more evidence",
            "before proposing",
            "cannot safely",
            "insufficient evidence",
            "i would need more evidence",
        ]
        clarify_tokens = [
            "would you like",
            "can you clarify",
            "need more information",
            "please provide",
            "what do you mean",
            "what should",
        ]

        if any(token in lower for token in refusal_tokens):
            return "REFUSAL"
        if any(token in lower for token in abstain_tokens):
            return "ABSTENTION"
        if any(token in lower for token in clarify_tokens) or "?" in lower:
            return "REQUEST_FOR_CLARIFICATION"
        return "NORMAL_CONCLUSION"

    def _classify_operator_state(self) -> tuple[str, str, str]:
        model_class = self._classify_model_response_text(self._last_model_response_text)

        if self._has_blocked_stage:
            return "BLOCKED", "explicit blocked stage present", model_class
        if self._tool_result_any_failure and self._has_guarding_stage:
            return "BLOCKED", "failed tool result with guarding decision", model_class
        if self._tool_result_any_failure:
            return "ERROR", "failed tool result without blocked stage", model_class
        if self._has_guarding_stage:
            return "GUARDING", "explicit guarding stage present", model_class

        if model_class == "REFUSAL":
            return "GUARDING", "model-only refusal classification", model_class
        if model_class == "ABSTENTION":
            return "GUARDING", "model-only abstention classification", model_class
        if model_class == "REQUEST_FOR_CLARIFICATION":
            return "CLARIFYING", "model-only clarification classification", model_class

        if self._has_final_conclusion:
            return "COMPLETED", "final conclusion stage present with no stronger blocking evidence", model_class
        if self._has_model_response:
            return "COMPLETED", "model response present with no stronger blocking evidence", model_class
        return "UNKNOWN", "insufficient evidence for terminal classification", model_class

    def _emit_verbose_block(self) -> None:
        width = 54
        self._emit("\n╭─────────────── L.I.S.A. FLIGHT ───────────────╮")
        self._emit(f"│ 🦮 GUIDE  Project: {self._truncate(self.project_name, 35):<35} │")
        self._emit("│                                                  │")
        for line in list(self.history)[-7:]:
            self._emit(f"│ {self._truncate(line, 48):<48} │")
        self._emit("│                                                  │")

        current = "idle"
        if self.current_tool:
            current = f"{self.current_tool}"
            if self.current_target:
                current = f"{current} -> {self.current_target}"
        elif self.current_model and self.current_state == "thinking":
            current = f"thinking ({self.current_model})"
        elif self.current_state != "idle":
            current = self.current_state

        self._emit(f"│ Current: {self._truncate(current, 39):<39} │")
        self._emit("╰──────────────────────────────────────────────────╯")

    def _truncate(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    def _emit(self, text: str) -> None:
        try:
            self.stream.write(text + "\n")
            self.stream.flush()
        except Exception:
            pass
