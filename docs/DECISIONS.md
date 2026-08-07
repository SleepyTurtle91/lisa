# 📝 DECISIONS.md — Institutional Architecture Ledger

```
===================================================
L.I.S.A. ENGINEERING OPERATING SYSTEM
===================================================

Status      : APPROVED ARCHITECTURAL CONSTITUTION LEDGER
Version     : 1.7.0
Last Update : 2026-08-07

===================================================
```

---

## 🏛️ Architecture Decision Records (ADRs)

### Decision #001: Provider Independence & Boundary Rules
* **Status**: Accepted
* **Version**: v0.1
* **Scope**: Permanent
* **Reason**: Language models are probabilistic execution backends. The Runtime Kernel must NEVER import concrete provider adapters (e.g. `OllamaProvider`, `OpenAIProvider`).
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `tests/test_architecture_rules.py::test_rule_1_runtime_no_concrete_providers`.

---

### Decision #002: Deterministic Runtime Supremacy
* **Status**: Accepted
* **Version**: v0.2
* **Scope**: Permanent
* **Reason**: The Runtime owns lifecycle state, session management, tool validation, and workflow execution. AI providers only supply probabilistic reasoning.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `RuntimeState` machine and `BaseProvider.handshake()`.

---

### Decision #003: Pure Data Contracts
* **Status**: Accepted
* **Version**: v0.3
* **Scope**: Permanent
* **Reason**: `ProviderManifest`, `ProviderContext`, `ToolManifest`, `ToolContext`, `InferenceRequest`, `InferenceResponse`, `InferenceResult`, `ToolRequest`, and `ToolResult` are immutable pure dataclasses with zero behavioral methods.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `tests/test_architecture_rules.py::test_rule_3_manifests_are_pure_dataclasses`, `test_rule_4`, `test_rule_5`.

---

### Decision #004: Inverted Provider Selection
* **Status**: Accepted
* **Version**: v0.3
* **Scope**: Permanent
* **Reason**: Providers are selected by matching requested `Capability` enums against healthy manifests via `ProviderSelector`.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `ProviderSelector.select()` policy engine.

---

### Decision #005: Automated Architecture Enforcement
* **Status**: Accepted
* **Version**: v0.3
* **Scope**: Permanent
* **Reason**: Architectural layer laws must be enforced via CI tests, preventing architectural erosion over time.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `tests/test_architecture_rules.py`.

---

### Decision #006: Inference Engine Abstraction & Response Normalization
* **Status**: Accepted
* **Version**: v0.4
* **Scope**: Permanent
* **Reason**: `InferenceEngine` owns provider dispatch, single-shot retries, and normalizes raw provider payloads into standardized `InferenceResult` objects. `LisaSession` never calls `BaseProvider` directly.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `lisa/engine/inference.py` and `tests/test_engine.py`.

---

### Decision #007: Standardized Request / Result Subsystem Contracts
* **Status**: Accepted
* **Version**: v0.5
* **Scope**: Permanent
* **Reason**: Every runtime subsystem must expose a typed, immutable Request/Result pair (`InferenceRequest`/`InferenceResult`, `ToolRequest`/`ToolResult`, `WorkflowRequest`/`WorkflowResult`, `PluginRequest`/`PluginResult`).
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `lisa/engine/models.py` and `lisa/tools/base.py`.

---

### Decision #008: Exclusive Tool Execution via ToolExecutor
* **Status**: Accepted
* **Version**: v0.5
* **Scope**: Permanent
* **Reason**: Every tool must be resolved and executed exclusively via `ToolExecutor.execute_request(ToolRequest)`. Runtime, sessions, and providers must never invoke `tool.execute()` directly.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `tests/test_architecture_rules.py::test_rule_6_tool_execution_via_executor_only`.

---

### Decision #009: The Contract Runtime Pattern
* **Status**: Accepted
* **Version**: v0.5
* **Scope**: Permanent
* **Reason**: All new runtime subsystems must adhere strictly to the 9-part Contract Runtime Pattern (`Manifest`, `Context`, `Request`, `Result`, `Registry`, `Resolver/Selector`, `Executor`, `State`, `Tests`). No new architectural pattern may be introduced without demonstrating that existing patterns fail.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `docs/SUBSYSTEM_TEMPLATE.md` and `tests/test_architecture_rules.py`.

---

### Decision #010: Zero-Mock Golden Project Integration
* **Status**: Accepted
* **Version**: v0.6
* **Scope**: Permanent
* **Reason**: End-to-end integration tests must execute zero-mock vertical slices against `examples/golden_project` to ensure all runtime contracts compose accurately in real filesystem environments.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `tests/integration/test_vertical_slice.py`.

---

### Decision #011: Core Runtime Architecture Freeze
* **Status**: Accepted
* **Version**: v0.6.5
* **Scope**: Permanent
* **Reason**: The core foundation subsystems (`LisaRuntime`, `ProviderRuntime`, `InferenceEngine`, `ToolRuntime`, and the `Contract Runtime Pattern`) are architecture-frozen. Future work must extend through contracts and implementations without modifying core boundaries unless approved by a formal ADR.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `tests/test_architecture_rules.py` and `docs/ARCHITECTURE_SCORE.md`.

---

### Decision #012: Native Tool Calling Loop & Re-Inference Synthesis
* **Status**: Accepted
* **Version**: v0.7
* **Scope**: Permanent
* **Reason**: When an AI provider returns tool calls in `InferenceResponse`, `LisaSession` executes each call via `ToolExecutor.execute_request(ToolRequest)`, appends the `ToolResult` output to message history, and re-invokes `InferenceEngine` for multi-turn synthesis before returning the final response to the caller.
* **Supersedes**: -
* **Superseded By**: -
* **Enforcement**: `lisa/runtime/session.py` and `tests/test_tool_calling_loop.py`.
