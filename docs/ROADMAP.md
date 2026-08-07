# 🚀 ROADMAP.md — L.I.S.A. Release Roadmap & Performance Protocol

```
===================================================
L.I.S.A. ENGINEERING OPERATING SYSTEM
===================================================

Status      : APPROVED MILESTONE ROADMAP
Current Tag : v1.1.0 (Execution Path & Performance Optimization)
Target      : Context Compaction, Tool Schema Filtering & Telemetry

===================================================
```

---

## 🎯 Milestone Sequence & Version Policy

Version numbers in L.I.S.A. represent **proven operational capabilities in production project execution**.

---

### ✅ `v1.0.0-alpha` — The Foundation Release
* **Goal**: 3-Tier Layer Architecture (`Runtime Layer`, `Execution Layer`, `Infrastructure Layer`), governance constitution stack (`AGENTS.md`, `ARCHITECTURE.md`, `LAYER_MODEL.md`, `DECISIONS.md`, `SUBSYSTEM_TEMPLATE.md`, `VISION.md`), automated CI architecture rule enforcement (`test_architecture_rules.py`), zero-mock integration suite.

---

### ✅ `v0.7` — Native Tool Calling Loop & Re-Inference Synthesis
* **Goal**: ReAct execution loop (`InferenceEngine` $\rightarrow$ Provider `/api/chat` tool call request $\rightarrow$ `ToolExecutor` real filesystem read $\rightarrow$ Message History append $\rightarrow$ Re-Inference synthesis $\rightarrow$ Final response). Operational validation against `extro_pos`.

---

### 🟢 `v1.1.0` — Execution Path & Performance Optimization (Active Focus)
* **Objective**: Optimize inference speed, prompt efficiency, and token usage for local models.
1. **Tool Schema Filtering**: Only expose relevant tool schemas dynamically per session context to reduce model context overhead.
2. **Context Compaction & Token Budgeting**: Automatically compress redundant history and prevent repeated system prompt evaluation.
3. **Provider Telemetry & Profiling**: Track exact token counts, evaluation latency, and retry metrics in `InferenceResult`.
4. **Prompt Caching / Schema Optimization**: Pre-compile static tool definition schemas.

---

### ⏳ `v1.2.0` — Workflow Engine & State Machine
* **Objective**: Execute multi-step deterministic workflows defined in `BOOT.md` without bypass.

---

### ⏳ `v1.3.0` — Memory Runtime
* **Objective**: Persistent cross-session knowledge indexing and project profile memory.

---

### ⏳ `v2.0.0` — Multi-Project Operating Platform
* **Objective**: Unmodified execution across `ExtroPOS`, `Music Home`, `RetroStash`, and `Kakeibo`.
