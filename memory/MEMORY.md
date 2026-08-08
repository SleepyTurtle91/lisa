# 🧠 L.I.S.A. Project Memory & Continuation Checkpoint

**Last Updated**: 2026-08-08
**EOS Version**: 1.1.0
**Status**: 🔒 FROZEN & STABLE
**Test Suite**: 47/47 PASSing (`PYTHONPATH=/home/user/development/projects python3 -m unittest discover -s tests`)

---

## 🏛️ Core Architecture & Philosophy

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

### The 3 Responsibilities of L.I.S.A.
1. **Guide (Environmental Grounding)**:
   - Resolves relative paths deterministically against `SessionContext.project_path` (e.g. `BOOT.md` $\rightarrow$ `/workspace/Projects/retails/BOOT.md`).
   - Restricts filesystem tools from escaping project sandboxes.
2. **Guardian (Safety & Evidence Discipline)**:
   - Triggers `engineering_evidence` intent when engineering verbs (`implement`, `modify`, `fix`, `refactor`, `architect`, `inspect`, `debug`, `add`, `remove`, `change`) are detected.
   - Enforces `strict_evidence_gate` scaffolding: `must_read_file_before_proposing_code`, `never_substitute_generic_patterns_for_missing_evidence`, and zero unpermitted file edits.
3. **Recorder (Experimental Flight Recorder)**:
   - Streams lossless JSONL event logs to `~/.lisa/flight_recorder/<session_id>.jsonl` (EXP-FR-001).

---

## 🔬 BANDURA Evidence Chain (EXP-001 through PILOT-003)

| Checkpoint | Focus | Primary Finding | Confidence |
| :--- | :--- | :--- | :---: |
| **EXP-001** | Scaffolding Behavior Shift | Scaffolding converted hallucinated file unavailability into active tool inspection. | Low |
| **EXP-002** | Repeated Trial ($N=10$) | Tool adherence increased from **60% to 100%**; hallucinations reduced from **20% to 0%**. | Moderate |
| **EXP-003** | Dose-Response Scaffolding | **Level 2 (Explicit Tool Discipline)** was the observed Minimum Effective Scaffolding (MES). | Moderate |
| **EXP-004** | Complexity Matrix | **Level 2** maintained 100% success across Low, Medium, and High complexity tasks. | Moderate |
| **EXP-005** | Adaptive Escalation | **Adaptive Escalation (Condition C)** reached **100% task reliability** by escalating L2 $\rightarrow$ L4 on complex debugging. | Moderate |
| **PILOT-001** | Execution Evidence | Identified procedural knowledge vs execution evidence conflation in small models. | Moderate |
| **PILOT-002** | Environmental Grounding | Injected `project_path` into `ToolExecutor` to ground relative path resolution. | High |
| **PILOT-003** | Engineering Evidence Gate | Under `engineering_evidence` mode, `qwen3:1.7b` shifted from **0 tools (guessing)** to **8 active tool calls** and **0 unpermitted edits**. | High |

---

## 📂 Key Files & Code Locations

- [`VISION.md`](file:///home/user/development/projects/lisa/VISION.md): Architectural vision document.
- [`RESEARCH.md`](file:///home/user/development/projects/lisa/RESEARCH.md): BANDURA Evidence Base v0.1.
- [`telemetry/flight_recorder.py`](file:///home/user/development/projects/lisa/telemetry/flight_recorder.py): EXP-FR-001 Flight Recorder.
- [`engine/analyzer.py`](file:///home/user/development/projects/lisa/engine/analyzer.py): `TaskAnalyzer` with verb evidence gate detection.
- [`engine/planner.py`](file:///home/user/development/projects/lisa/engine/planner.py): `ExecutionPlanner` linking hardware load & scaffolding profiles.
- [`engine/construction.py`](file:///home/user/development/projects/lisa/engine/construction.py): `ModelConstructionEngine` handling domain scaffolding.
- [`models/profiles/engineering_evidence.yaml`](file:///home/user/development/projects/lisa/models/profiles/engineering_evidence.yaml): Evidence-first scaffolding profile.
- [`tools/dispatcher.py`](file:///home/user/development/projects/lisa/tools/dispatcher.py): `ToolExecutor` enforcing project path grounding.
- [`cli/repl.py`](file:///home/user/development/projects/lisa/cli/repl.py): Interactive REPL shell with BIOS boot sequence.
- [`/home/user/.local/bin/lisa`](file:///home/user/.local/bin/lisa): Global system CLI launcher executable.

---

## 🚀 How to Resume Next Session

1. Run `lisa` or `lisa doctor /home/user/development/projects/extro_pos` from any terminal.
2. Run test suite: `PYTHONPATH=/home/user/development/projects python3 -m unittest discover -s tests`.
