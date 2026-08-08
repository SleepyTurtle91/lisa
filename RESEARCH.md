# 🔬 PROJECT BANDURA — Experimental Baseline v0.1

> **"How can external cognitive structure change the effective task behavior of resource-constrained language models, and what is the minimum structure required for reliable execution?"**

---

## 🔒 Experimental Methodology & Layer Separation

All BANDURA experimental artifacts adhere strictly to a 3-layer separation:

```text
RAW EVIDENCE  (Immutable measurement: timestamp, model, hardware, latency, tokens, tool calls)
     │
     ▼
DERIVED MEASUREMENTS  (Calculated metrics: tool adherence %, hallucination %, tok/s, deltas)
     │
     ▼
INTERPRETATION  (Conservative researcher findings, confidence rating, limitations, next question)
```

---

## 📊 BANDURA Experiment Chain Summary (EXP-001 to EXP-005)

| Experiment | Question Evaluated | Evidence Class | Primary Observation | Confidence |
| :--- | :--- | :--- | :--- | :---: |
| **EXP-001** | Can scaffolding alter small model behavior? | Pilot Observation | Scaffolding converted hallucinated file unavailability into active tool inspection. | **Low** |
| **EXP-002** | Does the behavioral effect repeat across trials ($N=10$)? | Repeated Controlled Trial | Tool adherence increased from **60% to 100%**; hallucinations reduced from **20% to 0%**. | **Moderate** |
| **EXP-003** | What is the Minimum Effective Scaffolding (MES) dose? | Dose-Response Experiment | **Level 2 (Explicit Tool Discipline)** was the observed MES (100% adherence at 26.7s). Level 4 added +6.1s prompt overhead without extra gain. | **Moderate** |
| **EXP-004** | How does scaffolding interact with Task Complexity? | Response Surface Matrix | **Level 2** maintained 100% success across Low, Medium, and High complexity tasks. Level 4 induced over-exploration on Low tasks (228s latency) and prompt bloat on High tasks. | **Moderate** |
| **EXP-005** | Can adaptive escalation outperform fixed scaffolding? | Adaptive Escalation Flight | **Adaptive Escalation (Condition C)** reached **100% task reliability** by dynamically escalating to L4 on difficult debugging tasks (`T2`), whereas Fixed L2 reached 66.7% and Fixed L4 reached 33.3%. | **Moderate** |

---

## 🚨 PILOT-001 — Procedural Knowledge vs Execution Evidence

**Observed Behavior**:
Model followed `FACT / INFERENCE / UNKNOWN` structure, but conflated **Declared Procedure** (e.g. `BOOT.md` specifying "Run Level 1-5 smoke sequence") with **Executed Evidence** (e.g. stating "Smoke tests Level 1-5 were completed").

**Evidence Provenance Taxonomy**:

| Evidence Type | Definition & Verification Requirement |
| :--- | :--- |
| `FILE_FACT` | Directly observed text inside an inspected file. |
| `TOOL_FACT` | Output returned directly by a tool invocation. |
| `EXECUTION_FACT` | Output confirmed by a executed test or build command. |
| `USER_FACT` | Fact explicitly declared by the user in the prompt. |
| `INFERENCE` | Derived logic or deduction based on facts. |
| `UNKNOWN` | Uninspected or unverified component. |
| `CONFLICT` | Contradictory evidence across sources. |

---

## 🧭 PILOT-002 — Project Context Propagation & Environmental Grounding

**Observed Behavior**:
Session context established active project path (e.g. `/workspace/Projects/retails`), but relative filesystem tool calls (e.g. `BOOT.md`) were evaluated against CWD (`lisa`) rather than the active session `project_path`.

**Environmental Grounding Principle**:
"The orchestration layer must provide deterministic environmental context (`project_path`) to tools rather than requiring the language model to infer execution context from conversational instructions."

**Resolution**:
1. Injected `project_path` into `ToolExecutor.execute_request` to deterministically resolve relative paths against active project root.
2. Isolated deterministic REPL commands (`list`, `ls`, `dir`) to execute filesystem tools directly without LLM inference overhead.

---

## 🛠️ PILOT-003 — Engineering Evidence Discipline

**Observed Behavior**:
Engineering prompts (containing verbs: `implement`, `modify`, `fix`, `refactor`, `architect`, `inspect`, `debug`, `add`, `remove`, `change`) without mandatory evidence gates allowed small models to substitute generic programming patterns for missing repository evidence.

**Three Responsibilities of L.I.S.A.**:

```text
                 L.I.S.A.
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   TEACHER       GUARDIAN      LABORATORY
       │            │            │
 Instructions    Evidence     Measurement
 Skills          Boundaries   Telemetry
 Scaffolding     Tools        Experiments
 Knowledge       Validation   Results
```

**Resolution**:
1. Triggered `engineering_evidence` intent upon detecting engineering verbs in `TaskAnalyzer`.
2. Applied `strict_evidence_gate` scaffolding enforcing `must_read_file_before_proposing_code` and `never_substitute_generic_patterns_for_missing_evidence`.

**Empirical Behavioral Shift Results (PILOT-003 Flight)**:

| Metric | Baseline (Without Evidence Gate) | PILOT-003 (Engineering Evidence Mode) |
| :--- | :---: | :---: |
| **Tool Calls Invoked** | **0 tools** (pattern completion) | **8 tool calls** (repository inspection) |
| **Unpermitted Modifications** | Attempted file edits | **0 unpermitted file edits** |
| **Observed Hallucinations** | Present | **0 observed hallucinations** |
| **Scaffolding Tier** | Small / General | **HEAVY / `strict_evidence_gate`** |

> **Disciplined Scientific Finding**:
> "PILOT-003 observed a behavioral shift following the introduction of Engineering Evidence Mode. The scaffolded condition produced eight repository tool calls, performed inspection, produced no observed hallucinations, and made zero unpermitted file modifications while the task explicitly prohibited modification."

---

## 🧪 PILOT-005 — Environmental Grounding Regression (Absolute Path Mutation)

**Date**: 2026-08-08

**Observed Behavior**:
Fresh session bootstrap correctly identified active target project as `/workspace/Projects/retails`, but a subsequent filesystem interaction transformed an explicitly supplied absolute path into a home-prefixed path (observed mutation pattern: `/workspace/...` to `/home/user/workspace/...`).

**Important Separation**:
1. `boot.md` vs `BOOT.md` is Linux case sensitivity and filename correction behavior.
2. Absolute path mutation is an environmental grounding contract violation.

**Grounding Invariant**:
"An absolute filesystem path must remain authoritative and must never be prefixed with session `project_path` or user home directory."

**Regression Coverage Added**:
1. Absolute path remains unchanged during filesystem read tool resolution.
2. Relative path resolution remains grounded to session `project_path` during tool-calling loop.
3. Missing case-variant filenames produce explicit suggestions (`Did you mean 'BOOT.md'?`) without silent substitution.
4. Flight recorder now emits path-forensic stages: `task_received` -> `project_context` -> `tool_request` -> `path_resolution` -> `resolved_path` -> `tool_result` -> `model_response`.

**Interpretation**:
This finding validates the Guide Dog hypothesis distinction between cognition and perception. The failure mode is environmental grounding drift in the orchestration/tooling path, not necessarily model reasoning failure.

---

## 🧠 BANDURA Core Conceptual Model

```text
                         BANDURA
                    Research Program
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
     Knowledge Efficiency        Cognitive Scaffolding
             │                           │
             ▼                           ▼
       Relevant Knowledge          Relevant Guidance
             │                           │
             └─────────────┬─────────────┘
                           ▼
                    Context Construction
                           │
                           ▼
                      Model / Brain
                           │
                           ▼
                       Execution
                           │
                           ▼
                      Observation
                           │
                           ▼
                       Evaluation
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                 Success      Insufficient
                    │             │
                    ▼             ▼
                  Finish       Escalate
                                  │
                                  ▼
                             Reconstruct
                                  │
                                  └──────► Execute
```

---

## 📁 Immutable Artifact Registry

The raw experimental data for EXP-001 through EXP-005 is preserved in the following registry files:

- `benchmarks/ab_scaffolding_experiment_2026-08-08_091333.json` (EXP-001)
- `benchmarks/exp_002_artifact_2026-08-08_092358.json` (EXP-002)
- `benchmarks/exp_003_artifact_2026-08-08_093957.json` (EXP-003)
- `benchmarks/exp_004_artifact_2026-08-08_100521.json` (EXP-004)
- `benchmarks/exp_005_artifact_2026-08-08_101434.json` (EXP-005)

---

## 🗂️ Master Evidence Registry

| Family | ID | Title |
| :--- | :--- | :--- |
| PILOT | PILOT-001 | Procedural Knowledge vs Execution Evidence |
| PILOT | PILOT-002 | Project Context Propagation & Environmental Grounding |
| PILOT | PILOT-003 | Engineering Evidence Discipline |
| PILOT | PILOT-004 | Ambiguous Engineering Objective |
| PILOT | PILOT-005 | Environmental Grounding Regression (Absolute Path Mutation) |
| EXP | EXP-001 | Scaffolding Pilot |
| EXP | EXP-002 | Repeated Controlled Trial |
| EXP | EXP-003 | Scaffolding Dose Response |
| EXP | EXP-004 | Task Complexity / Scaffolding |
| EXP | EXP-005 | Adaptive Escalation |
| EXP-FR | EXP-FR-002 | Live Flight Activity Instrumentation |
| NE | NE-001 | Session / Kernel Contract |
| NE | NE-002 | Provider Registration |
| NE | NE-003 | Provider Registry |
| NE | NE-004 | Tool Execution / Dispatch |
| NE | NE-005 | Inference Engine |
| NE | NE-006 | Telemetry / Flight Recorder |
| NE | NE-007 | End-to-End Flight Trace |
| NE | NE-008 | Flight Console Activity Projection |
| NE | NE-009 | Refusal Classification Baseline |

---

## 🧪 NEW FINDING — Repeated Native Engineering Execution

**Date**: 2026-08-08

**Observed Behavior**:
Three controlled L.I.S.A.-grounded runs executed native runtime-contract tasks within the repository's actual mission boundary. Each run inspected the relevant runtime surface, identified a concrete contract gap, added or used a focused regression test, implemented a minimal correction, and verified the result with the test suite.

**Specific Observations**:
1. **Repository Identity / Scope Discipline**: Each run stayed within the L.I.S.A. runtime platform domain rather than fabricating unrelated subsystems.
2. **Perception → Evidence → Action → Verification**: Each run grounded itself in repository context before making changes, then validated the result through tests.
3. **Repeated Native Execution Across Different Surfaces**: The same pattern was observed across three distinct runtime-contract surfaces:
   - session context validation in the kernel lifecycle,
   - provider registration pre-initialization enforcement,
   - duplicate provider registration rejection in the provider registry.

**Evidence**:
- NE-001: kernel/session contract tests passed after enforcing validation of invalid session contexts.
- NE-002: kernel/provider registration tests passed after enforcing provider registration only during initialized runtime.
- NE-003: provider registry tests passed after rejecting duplicate providers.
- Full regression suite result: **50/50 tests passed**.

**Interpretation**:
This is a meaningful repeated native-engineering checkpoint, but it remains a bounded observation rather than proof of broad autonomous engineering capability. The correct claim is:

> **Native Engineering Execution — Repeated Observation:** Three controlled native L.I.S.A. engineering runs across separate runtime-contract surfaces demonstrated the same repository-grounded perception → diagnosis → minimal intervention → verification pattern.

---

## 🧪 PILOT-004 — Ambiguous Engineering Objective

**Date**: 2026-08-08

**Observed Behavior**:
A vague engineering request of the form "test the calculation" failed to produce repository-grounded investigation. The request was routed through a low-complexity path and then escalated to a medium-complexity path, but the model still did not identify a concrete calculation implementation or inspect relevant source files. Instead, it described available tool capabilities or asked for clarification rather than locating a candidate computation target in the repository.

---

## 🧪 NEW FINDING — Fresh End-to-End Flight Harness Execution

**Date**: 2026-08-08

**Observed Behavior**:
A fresh end-to-end harness run executed the repository runtime flow end to end and emitted an ordered flight trace containing objective receipt, target discovery, task analysis, model selection, scaffolding decisions, tool use, tool results, and final conclusion.

**Evidence**:
- Harness command executed successfully via `PYTHONPATH=/home/user/Projects python3 benchmarks/end_to_end_flight_harness.py`.
- Output reported a generated artifact at `/workspace/Projects/lisa/benchmarks/e2e_flight_2026-08-08_152731.json`.
- Recorded stages included: `objective_received`, `target_discovery`, `task_analysis`, `model_selection`, `scaffolding_decision`, `tool_call`, `tool_result`, and `final_conclusion`.

**Interpretation**:
The runtime now demonstrates a visible composition-level trace across the full session lifecycle. This is a meaningful evidence milestone for traceability and staged execution, but it remains a bounded observation rather than proof of fully autonomous target discovery or robust open-ended debugging.

---

## 🧪 ANALYSIS — BLIND-E2E-001 Artifact Review

**Date**: 2026-08-08

**Observed**:
- The artifact at [benchmarks/e2e_flight_2026-08-08_152731.json](benchmarks/e2e_flight_2026-08-08_152731.json) contains a complete runtime trace with ordered stages from objective receipt through final conclusion.
- The trace records a single repository inspection action: `read_file` targeting [AGENTS.md](AGENTS.md), followed by a successful tool result.
- The final response was a concise summary grounded in the read-file output.

**Derived**:
- The runtime executed a tool-grounded inspection flow and produced a structured trace of the session lifecycle.
- The target was not discovered from an unstructured blind objective; the prompt explicitly asked to inspect [AGENTS.md](AGENTS.md).
- The artifact therefore shows evidence of staged execution and evidence use, but not yet evidence of independent target discovery from an ambiguous objective.

**Interpreted**:
- This run is best understood as a traceability milestone rather than a proof of autonomous blind perception.
- The most important distinction is that the system’s perception path was guided by an explicit target, so the result should not be overstated as a fully blind or self-directed discovery run.

---

## 🧪 NEW FINDING — BLIND-E2E-002 Ambiguous Objective Flight

**Date**: 2026-08-08

**Observed**:
- A new blind-objective harness run executed with an intentionally ambiguous prompt: "Find a small defect in the runtime contract handling, fix it with the minimum necessary change, and verify the fix with tests. Do not modify unrelated behavior."
- The resulting artifact was written to [benchmarks/blind_e2e_2026-08-08_153203.json](benchmarks/blind_e2e_2026-08-08_153203.json).
- The trace included the expected staged sequence of objective receipt, target discovery, task analysis, model selection, scaffolding, tool usage, tool result, and final conclusion.

**Derived**:
- The runtime emitted a structured trace for an ambiguous objective.
- The system selected a repository inspection path and responded with a cautious, evidence-seeking conclusion rather than claiming a fix without support.

**Interpreted**:
- This is a stronger experiment than BLIND-E2E-001 because the objective no longer explicitly names a target.
- The result suggests the system can enter an evidence-gathering mode for ambiguous objectives, but it still does not yet demonstrate fully reliable autonomous target discovery or repair execution.

---

## 🧪 NEW FINDING — BLIND-E2E-003 Evidence Expansion Flight

**Date**: 2026-08-08

**Observed**:
- A new evidence-expansion blind flight executed with the same ambiguous objective, but allowed the system to perform multiple repository inspection steps before concluding.
- The artifact was written to [benchmarks/blind_e2e_evidence_2026-08-08_153418.json](benchmarks/blind_e2e_evidence_2026-08-08_153418.json).
- The trace shows multiple tool calls across the session runtime, end-to-end tests, and kernel lifecycle.

**Derived**:
- The system broadened its evidence search beyond a single file, which increased the amount of repository context visible to the flight.
- The final conclusion remained cautious and did not claim an unsupported defect fix.

**Interpreted**:
- This is a meaningful comparison point for the Guide Dog model: the system did not become more reckless when given more evidence access; instead, it used the additional inspection steps to remain disciplined.
- The result supports the hypothesis that the current limitation may be perception depth rather than a general willingness to guess, but it still does not establish fully reliable autonomous defect discovery.

---

## 🧪 NEW FINDING — BLIND-E2E-004 Evidence Synthesis Flight

**Date**: 2026-08-08

**Observed**:
- A new blind-objective harness executed with an explicit evidence-synthesis step after repository inspection.
- The artifact was written to [benchmarks/blind_e2e_synthesis_2026-08-08_153712.json](benchmarks/blind_e2e_synthesis_2026-08-08_153712.json).
- The run produced an explicit evidence-set style response that listed observations, relevance, confidence, and a conclusion.

**Derived**:
- The system did not arrive at a concrete defect target, but it did transform raw inspection into a structured evidence summary.
- This is a meaningful step toward testing the hypothesis that evidence synthesis may be the binding constraint rather than raw repository access.

**Interpreted**:
- The evidence-synthesis variant improved the explicitness of the reasoning path without producing a concrete fix target.
- This supports the next hypothesis that structured evidence synthesis may be a useful intermediate layer, but it does not yet confirm that such synthesis is sufficient for autonomous target selection.

---

## 🧪 NEW FINDING — BLIND-E2E-006 Target Selection Flight

**Date**: 2026-08-08

**Observed**:
- A new blind-objective harness executed with a target-selection prompt that received a candidate set only and was asked to rank, justify, and decide ACT or ABSTAIN.
- The artifact was written to [benchmarks/blind_e2e_selection_2026-08-08_154236.json](benchmarks/blind_e2e_selection_2026-08-08_154236.json).
- The run returned the candidate payload directly rather than a ranked selection decision.

**Derived**:
- The system did not yet demonstrate a proper target-selection stage; instead, it reproduced the input candidate data.
- This is valuable because it isolates the selector as the unresolved component rather than conflating it with perception or candidate generation.

**Interpreted**:
- The current pipeline can generate candidate structure, but the selection stage did not yet transform that structure into an ordered, justified decision.
- This points to a genuine selection/decision-formation bottleneck rather than a simple lack of repository access.

---

## 🧪 NEW FINDING — BLIND-E2E-007 Selection Protocol Validation

**Date**: 2026-08-08

**Observed**:
- A controlled selection-protocol validation run executed with an explicit contract that required ranking, scoring, supporting evidence, contradictory evidence, and either a selected candidate or ABSTAIN.
- The artifact was written to [benchmarks/blind_e2e_protocol_2026-08-08_154428.json](benchmarks/blind_e2e_protocol_2026-08-08_154428.json).
- The provider still returned the candidate payload unchanged rather than producing a ranked decision.

**Derived**:
- The issue does not appear to be limited to a vague prompt; the provider still failed to perform the requested selection transformation under a stricter protocol.
- This strengthens the interpretation that selection/decision formation is a real boundary in the current runtime model.

**Interpreted**:
- The evidence now points more strongly to a genuine selection-capability boundary rather than a simple prompting defect.
- The next step should focus on selection logic and guardrail behavior rather than additional repository inspection or more general scaffolding.

---

## 🧪 NEW FINDING — BLIND-E2E-008 Deterministic Selection Baseline

**Date**: 2026-08-08

**Observed**:
- A deterministic selection-baseline harness executed with a deliberately simple candidate set where the correct answer was obvious by numeric comparison.
- The artifact was written to [benchmarks/blind_e2e_deterministic_2026-08-08_154621.json](benchmarks/blind_e2e_deterministic_2026-08-08_154621.json).
- The provider again echoed the candidate payload instead of returning the expected selected ID.

**Derived**:
- Even in a trivial comparison case, the current selection path did not perform the requested selection transformation.
- This is a strong control experiment because the correct answer was mechanically obvious and did not depend on repository exploration or ambiguous evidence.

**Interpreted**:
- The current selection boundary appears to be real and not merely caused by complex engineering context.
- The unresolved problem is now tightly scoped to the selection/decision step itself.

---

## 🧪 NEW FINDING — BLIND-E2E-009 Provider Boundary Inspection

**Date**: 2026-08-08

**Observed**:
- The runtime now records explicit `model_request` and `model_response` events through the inference engine and flight recorder.
- A fresh deterministic-selection artifact was written to [benchmarks/blind_e2e_deterministic_2026-08-08_155105.json](benchmarks/blind_e2e_deterministic_2026-08-08_155105.json).
- The recorded request contained the selection instruction, and the recorded response contained the candidate payload unchanged.

**Derived**:
- The instrumentation captured the boundary precisely: the prompt reached the provider intact, and the provider returned the unchanged payload.
- The disappearance of the selection transformation occurred between the request and the returned content, within the tested provider/runtime path.

**Interpreted**:
- This is now a stronger boundary claim than "selection is hard": the tested L.I.S.A. provider/runtime path did not perform a trivial selection transformation even when the request was explicit and the candidate comparison was obvious.
- The next stage should remain observational and should focus on whether the behavior is provider-specific, prompt-specific, or due to a normalization/response-handling issue rather than changing selection architecture.

---

## 🧪 NEW FINDING — BLIND-E2E-010 Direct Provider Isolation

**Date**: 2026-08-08

**Observed**:
- The same deterministic selection prompt was sent directly to the live Ollama provider outside the L.I.S.A. orchestration path.
- The provider/model responded with the token `1` and a long reasoning trace, rather than returning the candidate payload or a structured selection.

**Derived**:
- The direct provider behavior is materially different from the deterministic harness provider stub that L.I.S.A. used earlier.
- The live model did not have the candidate set in the context of that direct run, so its output was an under-specified placeholder rather than a real selection decision.

**Interpreted**:
- The earlier L.I.S.A. result should be interpreted as a harness/provider-stub behavior observation, not as evidence that the live model would echo the candidate payload.
- The experiment now shows that the current selection behavior is strongly context-dependent and that a fair provider-vs-L.I.S.A. comparison requires supplying the same candidate context to both paths.

---

## 🧪 NEW FINDING — BLIND-E2E-011 Provider vs L.I.S.A. Selection A/B

**Date**: 2026-08-08

**Observed**:
- A matched A/B comparison was run with identical model, prompt, and candidate context for both the direct provider and the L.I.S.A. path.
- The artifact was written to [benchmarks/provider_vs_lisa_selection_2026-08-08_155823.json](benchmarks/provider_vs_lisa_selection_2026-08-08_155823.json).
- Both paths returned the correct selection `A` for the obvious candidate set.

**Derived**:
- When the same candidate context is supplied to both paths, the live provider and the L.I.S.A. path produce the same selection outcome.
- This sharply narrows the interpretation: the earlier echo behavior was not caused by a general provider-vs-L.I.S.A. integration failure under matched conditions.

**Interpreted**:
- The current evidence no longer supports the claim that L.I.S.A. is breaking selection in the simple deterministic case.
- The remaining unresolved question is not provider-vs-L.I.S.A. causality in this matched setup, but whether more complex selection tasks, ambiguity, or different prompt formulations expose a genuine boundary.

---

## 🧪 NEW FINDING — BLIND-E2E-012 Selection Complexity Ladder (Fast)

**Date**: 2026-08-08

**Observed**:
- A short selection-complexity ladder was run across three increasingly difficult candidate sets: deterministic, balanced, and contradictory.
- The artifact was written to [benchmarks/selection_complexity_ladder_fast_2026-08-08_161236.json](benchmarks/selection_complexity_ladder_fast_2026-08-08_161236.json).
- All three cases returned the same selection result `A`.

**Derived**:
- The simple selection task remained robust across the first three ladder steps.
- The complexity threshold was not crossed by these initial variants.

**Interpreted**:
- The current evidence suggests a gradual rather than abrupt boundary for selection reliability.
- The next step should be to increase the complexity more aggressively, especially by adding more candidates and more ambiguous evidence structure.

---

## 🧪 NEW FINDING — BLIND-E2E-013 Multi-Candidate Overlap Selection

**Date**: 2026-08-08

**Observed**:
- A new harness executed a single multi-candidate selection case with four overlapping candidates and an explicit ABSTAIN option.
- The artifact was written to [benchmarks/selection_complexity_004_2026-08-08_170857.json](benchmarks/selection_complexity_004_2026-08-08_170857.json).
- The model returned `C`, which matched the expected selection and was classified as a valid selection.

**Derived**:
- The first more aggressive complexity step still produced a correct single-choice result under the tested prompt.
- The boundary was not yet exposed by a four-candidate overlap case.

**Interpreted**:
- The selection stage remained stable even when the candidate set became larger and more overlapping.
- The next meaningful escalation should focus on more ambiguous evidence structure, weaker justification, or a stronger requirement to abstain when support is insufficient.

---

## 🧪 NEW FINDING — BLIND-E2E-014 Failure Reproduction Replay

**Date**: 2026-08-08

**Observed**:
- A replay harness executed the original selection prompt and the original candidate payload from the earlier failing selection artifact.
- The artifact was written to [benchmarks/replay_failure_condition_2026-08-08_172108.json](benchmarks/replay_failure_condition_2026-08-08_172108.json).
- The direct provider and the L.I.S.A. runtime path both produced a structured ranking and decision rather than a payload echo.

**Derived**:
- The earlier payload-echo anomaly did not reproduce under controlled replay of the original prompt and candidate payload.
- The current evidence supports the interpretation that the earlier failure was context-specific rather than a stable property of the selection prompt itself.

**Interpreted**:
- The selection boundary remains unresolved as a reproducible failure mode, but the evidence now points to a transient or context-dependent anomaly rather than a general selection failure.
- The next research step should focus on the Guardian/abstention boundary: whether the model can choose when evidence is justified and abstain when it is not.

---

## 🧪 NEW FINDING — BLIND-E2E-015 Guardian Boundary

**Date**: 2026-08-08

**Observed**:
- A new guardian-boundary harness executed two controlled cases: one with sufficient evidence and one with insufficient evidence.
- The artifact was written to [benchmarks/guardian_boundary_2026-08-08_172934.json](benchmarks/guardian_boundary_2026-08-08_172934.json).
- The strong-evidence case returned `ACT`, and the weak-evidence case returned `ABSTAIN`.

**Derived**:
- The model distinguished between actionable evidence and insufficient evidence under the tested contract.
- The current evidence supports the interpretation that the Guardian boundary is operable in a simple binary decision setting.

**Interpreted**:
- This is the first bounded checkpoint for the Guardian role: the system can choose to act when evidence is strong and to abstain when it is not.
- The next step should be to test this boundary under more realistic engineering ambiguity rather than assuming the simple case generalizes automatically.

---

## 🧪 NEW FINDING — E2E-Guardian-001 Perception-to-Authorization

**Date**: 2026-08-08

**Observed**:
- A new end-to-end guardian harness executed a repository-grounded evidence flow and derived a guardian decision from the resulting candidate payload.
- The strong-evidence artifact was written to [benchmarks/e2e_guardian_strong_2026-08-08_173728.json](benchmarks/e2e_guardian_strong_2026-08-08_173728.json).
- The weak-evidence artifact was written to [benchmarks/e2e_guardian_weak_2026-08-08_173728.json](benchmarks/e2e_guardian_weak_2026-08-08_173728.json).
- The strong case produced `ACT`; the weak case produced `ABSTAIN`.

**Derived**:
- The guardian decision can now be derived from the evidence produced by the preceding perception and candidate-generation steps rather than from a pre-labeled prompt.
- The new harness also recorded structured confidence, supporting-evidence IDs, and contradictory-evidence IDs alongside the decision.

**Interpreted**:
- This is the first bounded end-to-end authorization checkpoint: the system completed the full perception → evidence → candidate generation → guardian decision path and produced an authorization decision from the resulting evidence.
- The result is meaningful but still bounded; it does not yet prove generalized safety or robust autonomous judgment in open-ended engineering tasks.

**Additional Observation**:
- The first iteration of the chain produced a different outcome from the intended interpretation: a strong candidate plus a weak distractor was treated as mixed evidence and yielded `ABSTAIN`.
- That outcome exposed a decision-rule issue rather than a data-generation issue, and the rule was refined so that a dominant strong candidate now yields `ACT` while weak/contradictory evidence still yields `ABSTAIN`.
- This is useful research evidence because it shows the Guardian’s decision boundary is sensitive to the exact thresholding rule and should be stress-tested under repetition and perturbation.

---

## 🧪 NEW FINDING — BLIND-E2E-005 Candidate Generation Flight

**Date**: 2026-08-08

**Observed**:
- A new blind-objective harness executed with an explicit candidate-generation step after repository inspection.
- The artifact was written to [benchmarks/blind_e2e_candidates_2026-08-08_154059.json](benchmarks/blind_e2e_candidates_2026-08-08_154059.json).
- The run produced three candidate targets and explicitly listed supporting evidence, contradictory evidence, and confidence.

**Derived**:
- The system can now surface candidate engineering targets as a structured intermediate output rather than only producing a final abstention.
- It still did not select a single concrete defect target with sufficient support.

**Interpreted**:
- This is a meaningful diagnostic step: the pipeline can now separate candidate generation from final selection, which makes the decision boundary more inspectable.
- The result supports the next hypothesis that the unresolved bottleneck is in target selection and evidence thresholding rather than in raw repository inspection alone.

**Observed Sequence**:
1. The user requested a vague objective: "simple task, test the calculation if it's working".
2. The system routed the request through a low-complexity / small-model path.
3. The model responded with a directory-level summary rather than investigating actual calculation logic.
4. After the user clarified with "code logic", the system escalated to a medium-complexity / larger-model path.
5. The model still failed to identify a concrete calculation implementation or inspect source code.
6. No calculation test was executed and no relevant evidence was produced.

**Interpretation**:
This is a useful failure mode. It suggests that increasing model capability alone does not compensate for insufficient task grounding when the objective lacks an identifiable target. The key missing capability is not just reasoning quality, but repository target discovery: the system needs to identify what calculation or logic implementation is being referenced before selecting a model or scaffolding strategy.

**Bounded Claim**:
> **Ambiguous Engineering Objective Handling — Observed:** A vague engineering request did not trigger repository-grounded target discovery, and the system failed to convert the request into an evidence-based investigation without additional user specification.

---

## 🧪 NE-004 — Tool Execution / Dispatch Contract

**Date**: 2026-08-08

**Observed Behavior**:
A native L.I.S.A. engineering task focused on the tool execution / dispatch boundary was grounded in repository context, tested through a focused regression case, and verified successfully. The task exercised tool dispatch and project-relative path resolution rather than the kernel/provider surfaces from earlier runs.

**Evidence**:
- A regression test was added for project-relative path resolution through the tool executor.
- Focused tool tests passed: **2/2**.
- Full regression suite result: **51/51 tests passed**.

**Interpretation**:
This is a separate bounded observation from PILOT-004. It demonstrates successful native engineering execution on the tool-execution surface, but it does not by itself validate the target-discovery hypothesis from PILOT-004.

**Bounded Claim**:
> **Tool Execution Contract — Demonstrated:** A native L.I.S.A. engineering task on the tool execution / dispatch boundary was grounded, tested, and verified successfully within the runtime-contract domain.

---

## 🧪 NE-005 — Inference Engine / Provider Selection Contract

**Date**: 2026-08-08

**Observed Behavior**:
A native L.I.S.A. engineering task focused on the inference engine / provider selection boundary was grounded in repository context, exercised through a focused regression case, and verified successfully. The task covered provider selection and response normalization rather than the earlier kernel/provider/dispatch surfaces.

**Evidence**:
- A regression test was added for inference engine execution against a registered provider.
- Focused inference-engine tests passed: **3/3**.
- Full regression suite result: **52/52 tests passed**.

**Interpretation**:
This is another bounded observation in the same runtime-contract domain. It broadens the evidence surface to the inference layer without claiming general autonomous engineering capability.

**Bounded Claim**:
> **Inference Engine Contract — Demonstrated:** A native L.I.S.A. engineering task on the inference engine / provider selection boundary was grounded, tested, and verified successfully within the runtime-contract domain.

---

## 🧪 NE-006 — Telemetry / Flight Recorder Evidence Layer

**Date**: 2026-08-08

**Observed Behavior**:
A native L.I.S.A. engineering task focused on the telemetry / flight recorder boundary was grounded in repository context, tested through a focused regression case, and verified successfully. The task exercised evidence persistence and event ordering rather than execution logic itself.

**Evidence**:
- A regression test was added for preserving event ordering and payload integrity in the flight recorder.
- Focused telemetry tests passed: **2/2**.
- Full regression suite result: **53/53 tests passed**.

**Interpretation**:
This is a distinct observation from the execution surfaces above. It strengthens the evidence layer of the system by showing that the repository can record and preserve runtime evidence in a testable way.

**Bounded Claim**:
> **Evidence Layer Contract — Demonstrated:** A native L.I.S.A. engineering task on the telemetry / flight recorder boundary was grounded, tested, and verified successfully within the runtime-contract domain.

---

## 🧪 NE-007 — Composition-Level End-to-End Flight Trace

**Date**: 2026-08-08

**Observed Behavior**:
A native L.I.S.A. engineering task was exercised as a single traceable flight rather than as an isolated set of kernel, provider, tool, and telemetry interactions. The runtime emitted a structured sequence of stages from objective receipt through tool execution to final conclusion, and the same events were persisted by the flight recorder.

**Evidence**:
- A regression test was added to verify end-to-end trace emission across runtime initialization, provider registration, tool execution, and final synthesis.
- Focused end-to-end flight test passed: **1/1**.
- A second regression test was added for a blind-objective run to verify discovery and decision-stage emission.
- Full regression suite result: **54/54 tests passed**.
- A concrete flight artifact was generated and recorded under the benchmarks directory.

**Interpretation**:
This is the first bounded checkpoint that shifts the evidence from component validation to composition validation. It demonstrates that the runtime can produce an ordered, inspectable end-to-end flight trace and can now expose discovery, analysis, model-selection, and scaffolding stages as part of the same flight. It does not yet establish that the system independently performs reliable target discovery or autonomous decision-making in a fully open-ended objective; those remain distinct research questions for later blind flights.

**Bounded Claim**:
> **Composition-Level Flight Trace — Demonstrated:** A native L.I.S.A. engineering task produced a structured end-to-end trace that connected runtime initialization, tool use, and final synthesis into one observable flight. This validates traceability of composition and the presence of explicit discovery/decision stages, not full autonomous capability.

---

## 🧪 NE-008 — Flight Console Activity Projection (Operator Layer)

**Date**: 2026-08-08

**Observed Behavior**:
An operator-facing live activity layer was added as a projection of real flight-recorder events rather than an independent state machine. The same event stream now feeds both persistent JSONL evidence and REPL-visible status lines.

**Evidence**:
- `FlightRecorder` now supports live subscriber callbacks in addition to JSONL persistence.
- A `FlightConsole` renderer consumes `model_request`, `model_response`, and `flight_stage` events and renders compact/verbose/off activity modes.
- REPL integration binds `FlightConsole` to the runtime recorder and exposes `activity <off|compact|verbose>` controls.
- Added regression coverage for subscriber delivery and activity rendering behavior.

**Interpretation**:
This adds an operator diagnostic surface without introducing a second synthetic execution-state model. The live console remains bounded by recorded runtime events, which strengthens observability while preserving evidence discipline.

**Bounded Claim**:
> **Operator Activity Layer — Demonstrated:** L.I.S.A. now projects real runtime flight events to a live console layer and persistent logs through a single event source, improving operational transparency without decoupling UI state from runtime evidence.

---

## 🧪 EXP-FR-002 — Live Flight Activity Instrumentation

**Date**: 2026-08-08

**Goal**:
Expose real-time L.I.S.A. state in the terminal as a truthful projection of runtime flight events while preserving Flight Recorder JSONL as the authoritative evidence source.

**Observed Behavior**:
- The activity renderer now maps live events to explicit operational states: `Orienting`, `Looking`, `Thinking`, `Planning`, `Using`, `Waiting`, `Guarding`, `Recording`, `Completed`, and `Blocked`.
- Model/provider wait and tool-result wait are now distinguishable in console output.
- Guardian and blocked decisions are surfaced from real stage events (`guarding_decision`, `blocked`) and model-response evidence.

**Acceptance Criteria Status**:
1. Every visible activity corresponds to a real runtime event: **Satisfied**.
2. No fake thinking animation while idle: **Satisfied**.
3. Tool name displayed during execution: **Satisfied**.
4. Target/path displayed when available: **Satisfied**.
5. Model/provider waiting distinguishable from tool waiting: **Satisfied**.
6. Guardian decisions visible: **Partially satisfied** (validated for explicit `guarding_decision` stages; one live capability-refusal flight rendered `Completed` instead of `Guarding`).
7. Errors visible: **Satisfied**.
8. Persisted JSONL remains authoritative: **Satisfied**.
9. UI rendering failure cannot affect runtime execution: **Satisfied** (subscriber exceptions are isolated).
10. Existing tests remain green: **Satisfied** in targeted regression runs.

**Evidence**:
- Recorder subscriber API and activity renderer integration with REPL runtime.
- Regression coverage expanded for subscriber delivery, state rendering, and blocked/guarding stage emission.

**Interpretation**:
This experiment is an instrumentation milestone, not a cognition milestone. It increases laboratory observability and falsifiability by projecting raw runtime evidence in real time without introducing an independent UI state machine.

---

## 🧪 EXP-FR-002-LIVE — Operator Flight Validation (A/B/C)

**Date**: 2026-08-08

**Goal**:
Validate that live REPL activity projection remains faithful to the same runtime evidence persisted in JSONL flight traces.

**Observed Behavior**:
- **Flight A (`read BOOT.md`)**: console showed `Using -> Waiting -> Looking -> Tool result`; JSONL recorded `tool_request`, `path_resolution`, `resolved_path`, `tool_result(success=true)` with resolved target `/workspace/Projects/retails/BOOT.md`.
- **Flight B (`read boot.md`)**: console showed `Using -> Waiting -> Looking -> Blocked`; JSONL recorded `tool_request`, `path_resolution`, `resolved_path`, `tool_result(success=false)` and filesystem error preserved case-sensitive suggestion (`Did you mean 'BOOT.md'?`).
- **Flight C (`define retails project`)**: console showed orienting/planning/thinking/waiting and then `Completed`; JSONL recorded `model_request` and a refusal-style `model_response` with no tool call. The monitor did not surface `Guarding/Blocked` for this refusal text path.

**Evidence**:
- Console captures: `/tmp/expfr2_flight_a.out`, `/tmp/expfr2_flight_b.out`, `/tmp/expfr2_flight_c.out`.
- Flight traces: `~/.lisa/flight_recorder/repl_retails_20260808_185352.jsonl`, `~/.lisa/flight_recorder/repl_retails_20260808_185525.jsonl`, `~/.lisa/flight_recorder/repl_retails_20260808_185536.jsonl`.

**Interpretation**:
Live validation confirms strong projection fidelity for direct tool flights (A/B). One model-refusal path (C) revealed a diagnostic gap: refusal language variant (`not able`) bypassed current guarding classification heuristic and appeared as `Completed`. This is now a bounded instrumentation bug, not a runtime execution bug.

**Bounded Claim**:
> **Live Projection Fidelity — Partially Demonstrated:** EXP-FR-002 live flights show console and JSONL agreement for successful and filesystem-failure tool paths, with one identified divergence on model refusal classification that should be resolved in the next instrumentation patch.

---

## 🧪 NE-009 — Refusal Classification Baseline

**Date**: 2026-08-08

**Observed Behavior**:
Executed a controlled live-response capture across six prompts to collect real model refusal, clarification, and failure-adjacent outcomes before altering renderer semantics.

**Evidence**:
- Artifact: `benchmarks/ne_009_refusal_classification_2026-08-08_190310.json`.
- Per-case raw recorder traces:
     - `benchmarks/ne009_C1_20260808_190044.jsonl`
     - `benchmarks/ne009_C2_20260808_190050.jsonl`
     - `benchmarks/ne009_C3_20260808_190103.jsonl`
     - `benchmarks/ne009_C4_20260808_190111.jsonl`
     - `benchmarks/ne009_C5_20260808_190213.jsonl`
     - `benchmarks/ne009_C6_20260808_190222.jsonl`
- Derived label counts (baseline run):
     - `REQUEST_FOR_CLARIFICATION`: 3
     - `REFUSAL`: 1
     - `ERROR`: 2

**Interpretation**:
This baseline confirms the necessity of separating refusal semantics from generic completion semantics in model-only paths. It also reveals an important instrumentation nuance: a failed tool stage may coexist with a later narrative model response, so operator display logic should anchor on stage evidence rather than prose style alone.

**Bounded Claim**:
> **Refusal Dataset — Demonstrated:** L.I.S.A. now has a real refusal-classification baseline artifact and per-case raw traces suitable for defining Guarding vs Blocked vs Clarifying semantics without altering the underlying runtime evidence model.

---

## 🧪 NE-009.1 — Evidence Precedence Semantic Contract

**Date**: 2026-08-08

**Observed Behavior**:
A deterministic classifier replayed the six NE-009 raw trace cases and derived terminal operator states using evidence precedence rules, without LLM assistance and without runtime or renderer modifications.

**Evidence**:
- Source dataset: `benchmarks/ne_009_refusal_classification_2026-08-08_190310.json`.
- Derived artifact: `benchmarks/ne_009_1_evidence_precedence_2026-08-08_190907.json`.
- Applied precedence order:
     1. explicit `blocked` stage,
     2. failed tool result + `guarding_decision`,
     3. failed tool result,
     4. explicit `guarding_decision`,
     5. model-only refusal/abstention/clarification,
     6. generic completion.
- Predicted operator-state counts:
     - `CLARIFYING`: 3
     - `GUARDING`: 1
     - `BLOCKED`: 2

**Interpretation**:
NE-009.1 supports a strong contract candidate: weak linguistic evidence should never override stronger runtime evidence. Model-response semantics remain useful, but only in model-only paths where stage/tool terminal evidence is absent.

**Bounded Claim**:
> **Evidence Precedence — Demonstrated:** A deterministic, non-LLM semantic pass over real NE-009 traces can classify operator terminal states by prioritizing runtime stage/tool evidence over response prose.
