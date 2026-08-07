# 🏛️ L.I.S.A. Layer Model Specification

```
===================================================
L.I.S.A. ENGINEERING OPERATING SYSTEM
===================================================

Status      : APPROVED ARCHITECTURE CONSTITUTION
Version     : 1.0.0
Mode        : Architectural Boundary & Layer Rules

===================================================
```

---

## 📐 The 3-Tier Layer Hierarchy

```text
┌─────────────────────────────────────────────────────────┐
│                     RUNTIME LAYER                       │
│  LisaRuntime  •  Session  •  Bootstrap  •  Workflow     │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│                    EXECUTION LAYER                      │
│  ProviderRuntime  •  ToolRuntime  •  PluginRuntime     │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│                  INFRASTRUCTURE LAYER                   │
│  OllamaAdapter  •  OpenAIAdapter  •  Filesystem  •  DB   │
└─────────────────────────────────────────────────────────┘
```

---

## ⚖️ Layer Boundaries & Import Rules

1. **Runtime Layer (`lisa.core`, `lisa.runtime`, `lisa.bootstrap`)**
   * **Owns**: Kernel lifecycle, session management, event bus, system state machines.
   * **May Depend On**: Execution Layer abstractions (`BaseProvider`, `BaseTool`, `ProviderRegistry`, `ProviderSelector`).
   * **MUST NEVER Import**: Infrastructure Layer concrete adapters (`OllamaProvider`, `OpenAIProvider`).

2. **Execution Layer (`lisa.providers`, `lisa.tools`, `lisa.plugins`)**
   * **Owns**: Schema compilation, validation, capability selection, dispatching, and manifest registries.
   * **May Depend On**: Pure data objects (`ProviderManifest`, `ProviderContext`, `Capability`) and typed errors.
   * **MUST NEVER Import**: Concrete infrastructure implementations or Runtime orchestration state.

3. **Infrastructure Layer (`lisa.providers.ollama`, `lisa.providers.openai`, `lisa.tools.filesystem`, etc.)**
   * **Owns**: Concrete API adapters, network connections, file I/O, device drivers.
   * **May Depend On**: `BaseProvider`, `BaseTool`, `ProviderManifest`, `Capability`.
   * **MUST NEVER Import**: Runtime kernel, session context, or execution orchestrators.

---

## 📊 Subsystem Maturity Index

| Subsystem | Maturity Level | Status |
| :--- | :--- | :--- |
| **Runtime Kernel** | **Stable** | State machines, event bus, typed exceptions verified. |
| **Provider Runtime** | **Stable** | Registry, manifest, capability selection, handshake verified. |
| **Tool Runtime** | **Alpha** | Validation, compilation, isolated execution verified. |
| **Workflow Runtime** | **Prototype** | Discovery and bootstrap engine initialized. |
| **Plugin Runtime** | **Design** | Extension interfaces defined. |
| **Memory Runtime** | **Design** | Context budgeting specified. |
