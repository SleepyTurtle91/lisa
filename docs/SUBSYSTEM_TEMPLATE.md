# 📋 SUBSYSTEM_TEMPLATE.md — Canonical Subsystem Architecture Protocol

```
===================================================
L.I.S.A. ENGINEERING OPERATING SYSTEM
===================================================

Status      : APPROVED ARCHITECTURE CONSTITUTION TEMPLATE
Version     : 1.0.0

===================================================
```

---

## 🏛️ The Contract Runtime Pattern

Every subsystem in L.I.S.A. (Providers, Tools, Workflows, Plugins, Memory) MUST follow the standardized **Contract Runtime Pattern**.

```text
Manifest ──► Context ──► Request ──► Resolver/Selector ──► Executor ──► Result
```

---

## 📐 Subsystem Checklist

When creating or refactoring any runtime subsystem, the implementation MUST supply all 9 required components:

| Component | Class / Artifact | Primary Responsibility | Immutability Rule |
| :--- | :--- | :--- | :--- |
| **1. Manifest** | `[Domain]Manifest` | Subsystem identity, capabilities, permissions, state | Pure Dataclass (Zero behavior) |
| **2. Context** | `[Domain]Context` | Execution parameters (session ID, budget, directory) | Pure Dataclass (Zero behavior) |
| **3. Request** | `[Domain]Request` | Input payload specifying target operation & arguments | Immutable Dataclass (`frozen=True`) |
| **4. Result** | `[Domain]Result` | Execution outcome, output, error, latency/duration | Immutable Dataclass (`frozen=True`) |
| **5. Registry** | `[Domain]Registry` | Stores registered component manifests & active instances | Standard Registry class |
| **6. Resolver / Selector** | `[Domain]Resolver` | Resolves or selects target instance by capability/state | Policy Engine |
| **7. Executor** | `[Domain]Executor` | Handles execution, retries, and error isolation | Execution Manager |
| **8. Lifecycle State** | `[Domain]State` | Enum defining explicit state machine states | `Enum` |
| **9. Tests** | `test_[domain].py` | Resilience matrix + Architectural Rule enforcement | Automated CI Verification |

---

## 🛑 Subsystem Boundary Rules
1. **Request/Result Only**: Callers outside the subsystem must communicate strictly via typed `Request` and `Result` dataclasses.
2. **Executor Isolation**: Calling code MUST NEVER invoke internal execution methods directly (e.g. `tool.execute()` or `provider.chat()`). Execution flows exclusively through `[Domain]Executor`.
3. **Pure Data Objects**: Manifests, Contexts, Requests, and Results MUST remain pure dataclasses with zero behavioral methods.
