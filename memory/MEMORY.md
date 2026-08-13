# 🧠 L.I.S.A. Project Memory & Continuation Checkpoint

**Last Updated**: 2026-08-08
**EOS Version**: 1.1.0
**Status**: 🔒 IMPLEMENTATION LOCKED AT NE-010.2 HUMAN REVIEW BOUNDARY
**Workspace Root**: `/home/user/Projects/lisa`
**Checkpoint**: `NE-009.2 frozen` / `NE-010.1 automated stress fidelity passed` / `NE-010.2 blinded reviewer packets generated and validated`

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

## 🔒 Current Experimental Lock

- **NE-009.2**: Frozen. Evidence-precedence classifier is integrated into `FlightConsole`, replayed against frozen C1-C6 traces, and validated on live A/B/C flights.
- **NE-010.1**: Passed. Automated operator-fidelity evaluator validated baseline and harder-profile flights with no observed `FlightConsole` projection failure after evaluator rubric refinement.
- **NE-010.2**: Infrastructure complete. Blind reviewer packets are generated, leak-checked, and ready for independent human reconstruction.
- **Lock Rule**: Do not modify `FlightConsole` or its semantics until NE-010.2 human-review results provide evidence that changes are necessary.

---

## 🔬 Current Evidence Frontier

### NE-009.2 — Evidence Precedence Integrated
- Deterministic precedence contract wired into live projection.
- Frozen acceptance replay passed `6/6`.
- Live A/B/C agreement achieved:
       - `read BOOT.md` $\rightarrow$ `COMPLETED`
       - `read boot.md` $\rightarrow$ `BLOCKED`
       - `define retails project` $\rightarrow$ `GUARDING`

### NE-010 — Operator Perception Fidelity
- Baseline automated fidelity run passed `4/4` flights.
- Harder-profile automated fidelity run passed `5/5` flights with `0` hard failures after refining the evaluator to score only operator-expected visible checkpoints.
- Initial harder-profile failures were evaluator false positives, not observed `FlightConsole` failures.
- NE-010.2 reviewer packets are byte-identical, leak-free, and separated from the truth key.

---

## 🔬 Historical BANDURA Evidence Chain (EXP-001 through PILOT-003)

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

- `RESEARCH.md`: canonical bounded findings and interpretations.
- `PROGRESSION_LOG.md`: append-only operational milestone log.
- `DISCOVERY.md`: emerging observations and open questions.
- `telemetry/activity_renderer.py`: operator-facing live projection surface.
- `telemetry/flight_recorder.py`: authoritative raw event stream and JSONL persistence.
- `runtime/session.py`: staged runtime flight emission and tool/model orchestration.
- `benchmarks/ne_009_2_renderer_replay.py`: frozen precedence replay harness.
- `benchmarks/ne_010_operator_perception_fidelity.py`: automated fidelity evaluator and blind review packet exporter.
- `tests/test_activity_renderer.py`: renderer semantics and cross-flight reset coverage.
- `tests/test_ne_010_operator_perception_fidelity.py`: evaluator and blind-packet regression coverage.

---

## 🚀 How to Resume Next Session

1. Do not edit `FlightConsole` before human-review evidence arrives.
2. Hand reviewer packets to two independent humans without the truth key:
       - `benchmarks/ne_010_2_reviewer_a_packet_2026-08-08_194418.md`
       - `benchmarks/ne_010_2_reviewer_b_packet_2026-08-08_194418.md`
3. Keep the truth key separate until scoring:
       - `benchmarks/ne_010_2_truth_key_2026-08-08_194418.json`
4. When code validation is needed, use focused checks:
       - `PYTHONPATH=/home/user/Projects /home/user/Projects/lisa/.venv/bin/python -m unittest tests/test_activity_renderer.py`
       - `PYTHONPATH=/home/user/Projects /home/user/Projects/lisa/.venv/bin/python -m unittest tests/test_ne_010_operator_perception_fidelity.py`
