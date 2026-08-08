# 🧠 L.I.S.A. Core Vision & Philosophy

> **"L.I.S.A. does not replace the intelligence of an AI model. It provides the engineering discipline, context, tools, constraints, feedback, and verification required for that intelligence to be useful."**

---

## 🏫 Brain + Teacher Mental Model

```text
                  L.I.S.A.
                 "Teacher"
                     │
                     │ teaches & scaffolds
                     ▼
              ┌──────────────┐
              │  AI MODEL    │
              │    "Brain"   │
              └──────────────┘
                     │
                     │ thinks
                     ▼
              Decision / Action
                     │
                     ▼
                 L.I.S.A.
                     │
                  verifies
                     │
             ┌───────┴───────┐
             ▼               ▼
          Correct          Wrong
             │               │
             ▼               ▼
           Continue       Feedback / Retry
```

### Deterministic vs. Probabilistic Boundary

* **AI Model (Operator / Brain)**: Probabilistic reasoning, code synthesis, hypothesis generation, language understanding.
* **L.I.S.A. Runtime (Guide Dog / Teacher)**: Environmental grounding, tool resolution, path sandboxing, mandatory evidence gates, telemetry & full-trace recording.

---

## 🦮 Operator + Guide Dog Mental Model

```text
                 REAL WORLD
                     │
              Repository / Files
              Tools / Environment
              Tests / Runtime
                     │
                     ▼
              ┌──────────────┐
              │    L.I.S.A.  │
              │  GUIDE DOG   │
              └──────┬───────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
      GUIDE       GUARDIAN     RECORDER
        │            │            │
   Environment    Safety /       Full
   grounding      evidence      trace
        │            │            │
        └────────────┼────────────┘
                     ▼
              ┌──────────────┐
              │   AI MODEL   │
              │   OPERATOR   │
              └──────┬───────┘
                     │
                  Reason
                  Decide
                  Generate
                     │
                     ▼
              L.I.S.A. checks
                     │
              ┌──────┴──────┐
              │             │
            Correct       Wrong / Insufficient
              │             │
              ▼             ▼
             DONE       Guide again
```

## 🎯 Cognitive Scaffolding by Model Tier

Different AI models require tailored instruction & workflow scaffolding:

1. **Small Tier (e.g. 1.7B)**:
   - *Strategy*: Stepwise explicit instructions, targeted file retrieval, evidence-first rule enforcement.
2. **Standard Tier (e.g. 4B / 8B)**:
   - *Strategy*: Guided modular workflow, boundary checking, unit test verification.
3. **Heavy / Cloud Tier (e.g. 30B / Gemini / Claude)**:
   - *Strategy*: Autonomous high-level architectural directives, multi-document dependency mapping, governance verification.

---

## 🏗️ Three-Layer Architectural Distinction

```text
             L.I.S.A.
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
   Knowledge Scaffold   Runtime
      │         │         │
   WHAT       HOW       CONTROL
      │         │         │
      └─────────┼─────────┘
                ▼
             LLM Brain
```

1. **Knowledge (WHAT)**: Source code, `BOOT.md`, `AGENTS.md`, `PROJECT_MEMORY.md`, documentation.
2. **Scaffolding (HOW)**: `ModelConstructionProfile` (`use_tools_for_facts`, `label_facts_vs_inferences_vs_unknowns`, `never_invent_uninspected_files`).
3. **Runtime (CONTROL)**: `TaskAnalyzer`, `ExecutionPlanner`, `ToolExecutor`, `ModelConstructionEngine`, `ExperimentRegistry`.
