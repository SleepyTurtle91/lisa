# 🏗️ ARCHITECTURE.md — Core Engineering Principles

```
===================================================
LISA RUNTIME ENGINEERING PRINCIPLES
===================================================

Status      : FROZEN ARCHITECTURE PRINCIPLE
Version     : 1.0.0

===================================================
```

## ⚖️ The Runtime-First Principle

> **"Every subsystem must remain fully functional without any specific AI provider."**

### Control Hierarchy

```text
               LisaRuntime (Kernel)
                        │
             ┌──────────┴──────────┐
             │                     │
       Tool Execution       Deterministic Workflow
             │                     │
             └──────────┬──────────┘
                        │
                AI Model Provider
           (Probabilistic Intelligence)
```

1. **Deterministic Execution First**: The `LisaRuntime` kernel owns session lifecycle, tool validation, context budgeting, and event dispatching.
2. **Provider Isolation**: Language models (`OllamaProvider`, `OpenAIProvider`, `ClaudeProvider`) supply probabilistic reasoning as interchangeable execution backends.
3. **Zero Vendor Lock-In**: Subsystems, tools, and workflows execute independently of model provider specifics.
