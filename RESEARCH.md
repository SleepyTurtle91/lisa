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

---

## 🧪 NE-010 — Operator Perception Fidelity

**Date**: 2026-08-08

**Observed Behavior**:
An automated evaluator reconstructed ground truth from recorder and model events, then compared that reconstructed truth against live FlightConsole projection without using final answer prose as a scoring source.

**Evidence**:
- Baseline artifact: `benchmarks/ne_010_operator_perception_fidelity_2026-08-08_193135.json`.
- Baseline JSONL trace: `benchmarks/ne_010_operator_fidelity_20260808_193003.jsonl`.
- Baseline result: **4/4 flights passed**, **0 hard failures**.
- Covered terminal semantic paths in the validated run: `CLARIFYING`, `BLOCKED`, `GUARDING`, `COMPLETED`.
- Safety-boundary rule enforced in evaluator: truth `BLOCKED`/`GUARDING` projected as `Completed` is a hard failure.

**Interpretation**:
This establishes the measurement mechanism for operator-fidelity testing: the system can now compare projection against recorder-derived truth without circularly trusting final answer prose. It validates evaluator architecture, not yet broad human-operator usefulness.

**Bounded Claim**:
> **Operator-Fidelity Measurement Path — Demonstrated:** L.I.S.A. can now score live console projection against recorder/model-derived truth using a deterministic evaluator that preserves hard-failure semantics for safety-boundary misprojection.

---

## 🧪 NE-010.1 — Stress Fidelity / Evaluator Contract Refinement

**Date**: 2026-08-08

**Observed Behavior**:
The harder-profile stress run initially reported two failures, but inspection showed those failures were caused by an overly broad visibility rubric that counted internal non-rendered events as operator-visible checkpoints. After refining the measurement contract to score visibility only on operator-expected visible checkpoints, the harder profile passed without FlightConsole changes.

**Evidence**:
- Initial harder-profile artifact: `benchmarks/ne_010_operator_perception_fidelity_2026-08-08_193653.json`.
- Initial result: **3/5 flights passed**, **0 hard failures**.
- Failure dimension in both failing flights: `timeline_visibility_fidelity` only.
- Refined harder-profile artifact: `benchmarks/ne_010_operator_perception_fidelity_2026-08-08_193939.json`.
- Refined JSONL trace: `benchmarks/ne_010_operator_fidelity_20260808_193731.jsonl`.
- Refined result: **5/5 flights passed**, **0 hard failures**.
- Regression coverage expanded for evaluator visibility logic and blind review packet export.

**Interpretation**:
The initial NE-010.1 failures were evaluator false positives, not observed FlightConsole projection failures. This is meaningful evidence about the measurement layer itself: operator-fidelity scoring must distinguish between internal diagnostic events and operator-facing checkpoints. After that refinement, the harder mixed-path flights still preserved console-to-truth agreement with no renderer modifications.

**Bounded Claim**:
> **Stress Fidelity — Demonstrated:** Under a harder mixed-path flight profile, FlightConsole projection remained aligned with recorder-derived truth after the evaluator contract was narrowed to operator-visible checkpoints, with no observed projection failure and no FlightConsole behavior changes.

---

## 🧪 NE-011 — Compound Intent / Target Extraction

**Date**: 2026-08-10

**Question**: When the human gives L.I.S.A. a target indirectly (embedded in natural-language phrasing), does it correctly extract what the human meant?

**Observed Behavior**:
Seven cases were run — 3 controls (unambiguous, bare-path prompts) and 4 compound cases (target embedded in natural-language phrasing). The harness recorded the first tool invocation for each case: tool name, path argument, and success status.

**Raw Evidence**:
- Artifact: `benchmarks/ne_011_compound_intent_2026-08-10_092224.json`
- Model: `qwen3:1.7b` via Ollama
- Project used: lisa repo root (`/workspace/Projects/lisa`)

| Case | Group | Prompt | Tool | path_arg | tool_ok | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C1 | CONTROL | `read README.md` | `read_file` | `README.md` | ✅ | DIRECT_PATH |
| C2 | CONTROL | `list docs` | — | — | — | NO_TOOL_CALL |
| C3 | CONTROL | `read docs/ARCHITECTURE_SCORE.md` | `read_file` | `docs/ARCHITECTURE_SCORE.md` | ✅ | DIRECT_PATH |
| X1 | COMPOUND | `read files inside docs` | `list_directory` | `docs` | ✅ | DIRECT_PATH |
| X2 | COMPOUND | `read docs and suggest a plan` | — | — | — | CLARIFICATION |
| X3 | COMPOUND | `inspect documentation before doing anything` | `list_directory` | `~/Documents/Documentation` | ❌ | DIRECT_PATH* |
| X4 | COMPOUND | `read /docs before we do anything` | `read_file` | `/docs` | ❌ | DIRECT_PATH* |

*DIRECT_PATH classification is too coarse for X3 and X4 — they require a finer category (see Interpretation below).

**Derived Measurements**:
- `COMPOUND_LITERAL` (original hypothesis — path arg contains compound prose): **0 / 7 cases**
- Controls passing cleanly: **2 / 3** (C2 is a control miss)
- Compound cases using a tool: **2 / 4** (X1 successful; X4 failed)
- Compound cases requesting clarification: **1 / 4** (X2)
- Compound cases hallucinating a path: **1 / 4** (X3)

**Interpretation**:

The original hypothesis — that L.I.S.A. passes compound phrases as literal path arguments — was **not confirmed** under these seven prompts. The model always extracted a plausible-looking path string rather than passing the raw phrase.

Three distinct failure modes were observed instead:

1. **Environmental Grounding Hallucination (X3)**: `inspect documentation before doing anything` produced `list_directory(path='~/Documents/Documentation')`. The model fabricated a path that does not exist in the project and has no basis in any project file or context. This is the most concerning failure: rather than querying the actual project structure, the model invented a plausible-sounding but entirely wrong target.

2. **Absolute Path / Tool Mismatch (X4)**: `read /docs before we do anything` correctly stripped the trailing clause and extracted `/docs`, but (a) used `read_file` on what is clearly a directory and (b) treated the path as absolute, which does not exist on the system. The intent-extraction itself partially succeeded; the failure is wrong tool selection and incorrect path absoluteness.

3. **Control Miss (C2)**: `list docs` (an unambiguous command) produced NO_TOOL_CALL — the model answered without invoking `list_directory`. This is a control-layer miss, not a compound intent failure.

**One positive finding**: X1 (`read files inside docs`) produced `list_directory(path='docs')` with a successful tool result. The model correctly interpreted "files inside docs" as a directory listing operation on `docs/`.

**Classification Gap Identified**:
The `DIRECT_PATH` label is too coarse to distinguish a valid resolution (C1, C3, X1) from a hallucinated path (X3) or a wrong-tool resolution (X4). A future harness refinement should introduce:
- `HALLUCINATED_PATH`: path arg has no correspondence to any project artifact and fails resolution
- `WRONG_TOOL_TYPE`: path is plausible but wrong tool selected for the target type (e.g., `read_file` on a directory)

**Bounded Claim**:
> **NE-011 Baseline — Established:** Under a 7-case compound-intent diagnostic, `COMPOUND_LITERAL` passthrough was not observed. The dominant failure modes were environmental grounding hallucination (model fabricates a non-existent path) and tool/path-type mismatch. One control case (`list docs`) also failed to invoke a tool, indicating the extraction boundary is not solely a compound-phrasing problem.

---

## 🧪 NE-011.1 — Refined Classification Replay

**Date**: 2026-08-10

**Question**: Can the NE-011 classification be refined to separate materially different sub-failures currently masked by the coarse `DIRECT_PATH` bucket?

**Method**: Deterministic replay of the NE-011 artifact through a refined classifier.  No new live model calls.  Follows the same replay-over-dataset pattern as NE-009.1.

**Refined classification contract** (applied in precedence order):
1. `tool_calls_made == 0` → `NO_TOOL_CALL` or `CLARIFICATION`
2. path arg contains prose markers → `COMPOUND_LITERAL`
3. `tool_success == True` → `DIRECT_PATH`
4. project-relative equivalent exists + wrong tool type → `WRONG_TOOL_TYPE`
5. no project-relative equivalent exists → `HALLUCINATED_PATH`
6. failure for another reason → `DIRECT_PATH` (with `failed_resolution=True`)

**Raw Evidence**:
- Source artifact: `benchmarks/ne_011_compound_intent_2026-08-10_092224.json`
- Refined artifact: `benchmarks/ne_011_1_refined_2026-08-10_093425.json`

| Case | NE-011 label | NE-011.1 label | Changed |
| :--- | :--- | :--- | :--- |
| C1 | DIRECT_PATH | DIRECT_PATH | — |
| C2 | NO_TOOL_CALL | NO_TOOL_CALL | — |
| C3 | DIRECT_PATH | DIRECT_PATH | — |
| X1 | DIRECT_PATH | DIRECT_PATH | — |
| X2 | CLARIFICATION | CLARIFICATION | — |
| X3 | DIRECT_PATH | **HALLUCINATED_PATH** | ← |
| X4 | DIRECT_PATH | **WRONG_TOOL_TYPE** | ← |

**Derived Measurements**:
- Compound distribution after refinement: `DIRECT_PATH=1, CLARIFICATION=1, HALLUCINATED_PATH=1, WRONG_TOOL_TYPE=1`
- Reclassification rate: 2 / 7 cases (both in COMPOUND group)
- No false movements: all CONTROL cases and X1/X2 retained their original label

**Interpretation**:
The refined classifier confirms the two distinct failure modes without altering any other label.  `HALLUCINATED_PATH` (X3) and `WRONG_TOOL_TYPE` (X4) are now separable from genuinely grounded path extraction (X1, C1, C3).

The distinction matters for the next experiment because the two failures call for different interventions:
- `HALLUCINATED_PATH` (X3) — the model lacked environmental evidence and invented a target; the hypothesis is that supplying project structure upfront would suppress this.
- `WRONG_TOOL_TYPE` (X4) — the model extracted the right target from the sentence but chose the wrong tool; this is a tool-selection problem, not a perception/grounding problem.

**Bounded Claim**:
> **NE-011.1 — Classifier Refinement Validated:** A deterministic replay of the NE-011 dataset through the refined classification contract correctly reclassified X3 as `HALLUCINATED_PATH` and X4 as `WRONG_TOOL_TYPE`, with no false movements on the five other cases.  The two sub-failure categories are now empirically separable.

---

## 🧪 NE-011.2 — Controlled A/B Environmental-Evidence Experiment

**Date**: 2026-08-10

**Question**: Does supplying repository structure upfront suppress grounding hallucination and produce a correctly-grounded target selection?

**Hypothesis**: Condition A (no context) → `HALLUCINATED_PATH`; Condition B (structure exposed) → `DIRECT_PATH`

**Probe prompt** (X3 from NE-011): `inspect documentation before doing anything`

**Method**: Two live model runs against the lisa repo root.  Classification uses the NE-011.1 refined contract.

**Raw Evidence**:
- Artifact: `benchmarks/ne_011_2_env_evidence_2026-08-10_093635.json`
- Model: `qwen3:1.7b` via Ollama

| Condition | Context supplied | Tool | path_arg | tool_ok | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A — no context | none | — | — | — | CLARIFICATION |
| B — structure exposed | project tree (depth 2) | `list_directory` | `docs` | ✅ | DIRECT_PATH |

Condition A response (verbatim excerpt):
> "I need to know the specific file or directory you want to inspect for documentation. Could you provide the path relative to the project workspace?"

Condition B response (verbatim excerpt):
> "The documentation files in the repository are: `MEMORY_ENGINE.md`, `DECISIONS.md`, `TOOL_API.md`, …"

**Derived Measurements**:
- Condition B correctly identified `docs/` and called `list_directory(path='docs')` with a successful result.
- Condition A produced no tool call and asked for clarification.
- Verdict: `PARTIAL` — the positive half of the hypothesis is confirmed (B → DIRECT_PATH); the negative half is not the exact baseline (A → CLARIFICATION, not HALLUCINATED_PATH as observed in NE-011 X3).

**Interpretation**:

The positive finding is unambiguous: **when the project tree was supplied, the model correctly identified `docs/` as the documentation target and called the right tool.**  This is direct evidence that environmental perception — not model reasoning capacity — was the missing element in the X3 failure.

The Condition A result (CLARIFICATION rather than HALLUCINATED_PATH) differs from the NE-011 X3 baseline.  Two interpretations are consistent with this:
1. **Non-deterministic baseline**: For this ambiguous prompt the model produces different failure modes across runs (hallucination in NE-011 X3, clarification-seeking here).  Both are ungrounded.  Neither produces a useful action.
2. **Context sensitivity**: Small differences in session state between runs may tip the model toward hallucination vs. asking.  The underlying mechanism is the same — absent environmental evidence, the model cannot act correctly.

In either case, the key architectural conclusion holds:

> **Without environmental evidence, the model cannot correctly ground an implicit target.  With it, the model grounds correctly and selects the right operation.**

This is a direct experimental test of the Guide Dog architecture:
```
No L.I.S.A. eyes → model invents or asks
L.I.S.A. eyes supplied → model sees and acts correctly
```

**Non-determinism caveat**: The HALLUCINATED_PATH→CLARIFICATION shift between X3 (NE-011) and Condition A (NE-011.2) means that running Condition A once is not sufficient to characterize the no-context failure distribution.  A future experiment should run Condition A N≥5 times and report the hallucination/clarification/other breakdown before claiming a stable baseline.

**Bounded Claim**:
> **NE-011.2 — Environmental Perception Hypothesis Partially Supported:** A single A/B pair shows that supplying project structure produced correct, grounded target selection (`list_directory('docs')` with success), while the same prompt without structure produced an ungrounded non-action (CLARIFICATION).  The positive direction is confirmed; the no-context baseline requires N-replication to characterize fully.

---

## 🧪 NE-012 — Intent & Context Grounding Baseline

**Date**: 2026-08-13

**Observed Behavior**:
A 6-case diagnostic harness evaluated natural intent extraction (Test A), target type grounding (Test B), and evidence provenance isolation (Test C) under live `qwen3:1.7b` execution.

**Evidence**:
- Artifact: `benchmarks/ne_012_intent_grounding_2026-08-13_091736.json`
- Test A (`read files inside docs`, `show me what's inside docs`): 100% intent extraction match (`LIST_DIRECTORY` with `path='docs'`).
- Test B (`list README.md`, `read docs`): Mismatch / fallback observed — `list README.md` invoked `list_directory(path='/')` root fallback; `read docs` resulted in `NO_TOOL_CALL`.
- Test C (`What has actually been verified in this session?`): Model abstained (`NO_TOOL_CALL`) and requested context rather than querying flight recorder evidence.

**Interpretation**:
1. Intent resolution is functional without an Intent Pre-Classifier (`A2/A3 → list_directory`).
2. Target-type grounding before tool invocation is missing (requires pre-invocation `stat` check).
3. Session provenance requires a queryable, recorder-backed epistemic evidence layer rather than model self-reflection.
4. `FlightConsole` remains locked (`NE-010.2`).

**Bounded Claim**:
> **NE-012 — Intent Resolution Validated, Type Grounding & Provenance Bottlenecks Isolated:** Natural intent extraction succeeds natively in small models, but pre-invocation target-type inspection (`stat`) and queryable epistemic evidence layers are necessary to eliminate fallback tool calls and provenance self-reflection failures.

---

## 🧪 NE-012.1 — Target Grounding & Epistemic Evidence Store

**Date**: 2026-08-13

**Observed Behavior**:
1. **Experiment A**: `TargetInspector` (`tools/filesystem/target_grounding.py`) deterministically inspects filesystem paths (`FILE`, `DIRECTORY`, `MISSING`) and enforces legal operation contracts in `ToolExecutor` before execution. Invalid tool calls (such as `list_directory` on `README.md`) are rejected prior to execution, preventing root `/` fallbacks.
2. **Experiment B**: `EvidenceStore` (`memory/evidence_store.py`) ingests raw `FlightRecorder` events into four structured epistemic categories (`OBSERVED`, `DOCUMENTED`, `INFERRED`, `UNVERIFIED`). Provenance queries return exact execution evidence rather than relying on model self-reflection.

**Evidence**:
- Unit tests: `tests/test_ne_012_target_grounding.py` (7/7 PASS), `tests/test_ne_012_evidence_store.py` (4/4 PASS).
- Artifact Exp A: `benchmarks/ne_012_1_expA_target_grounding_2026-08-13_092445.json`.
- Artifact Exp B: `benchmarks/ne_012_1_expB_evidence_store_20260813_092607.json`.
- Full regression suite: **86/86 PASS (100%)**.

**Interpretation**:
The Guide Dog architecture now enforces pre-invocation target grounding and exposes queryable session provenance from recorded events without altering `FlightConsole` or adding fragile intent pre-classifiers.

**Bounded Claim**:
> **NE-012.1 — Pre-Invocation Target Grounding & Epistemic Store Validated:** Target-type pre-inspection eliminates invalid tool execution before dispatch, and event-recorder ingestion enables authoritative session provenance queries without model conversational introspection.

---

## 🧪 NE-012.2 — End-to-End Grounded Session Integration Validation

**Date**: 2026-08-13

**Observed Behavior**:
Executed a 3-flight live integration harness (`benchmarks/ne_012_2_integration_validation.py`) to test whether `TargetInspector` and `EvidenceStore` compose correctly in end-to-end sessions:
1. **Flight A (`list README.md`)**: The model initially called `list_directory(path='/')` (root fallback). Because `/` is a directory, `TargetInspector` allowed execution. The model then attempted `list_directory(path='README.md')`, which `TargetInspector` intercepted and blocked before execution.
2. **Flight B (`list docs`)**: The model asked for explicit path clarification instead of executing a tool call.
3. **Flight C (`What has actually been verified in this session?`)**: Preceded by `read README.md`. `EvidenceStore` accurately ingested 5 `OBSERVED` tool events. However, when answering the provenance question, model prose conflated text found in `README.md` ("32/32 tests passed") with actual session verification.

**Evidence**:
- Artifact: `benchmarks/ne_012_2_integration_validation_2026-08-13_092844.json`.
- Traces: `benchmarks/ne012_2_Flight_A_*.jsonl` through `benchmarks/ne012_2_Flight_C_*.jsonl`.
- Full regression test suite: **86/86 PASS (100%)**.

**Interpretation**:
- This integration run validates the core architectural boundary: **epistemic provenance cannot rely on model conversational reasoning**. Small models conflate `DOCUMENTED` text in inspected files with `OBSERVED` execution.
- `EvidenceStore` must serve as an authoritative query boundary directly to the operator/runtime rather than passing ungrounded prose to the model.
- `FlightConsole` remains strictly locked (`NE-010.2`).

**Bounded Claim**:
> **NE-012.2 — Epistemic Provenance Isolation Conflation Confirmed:** Integration validation proves that models conflate `DOCUMENTED` text with `OBSERVED` execution during self-reflection, establishing that `EvidenceStore` must serve as the primary epistemic query boundary rather than delegating provenance synthesis to LLM prose.

---

## 🧪 NE-013 — Authoritative Evidence Boundary

**Date**: 2026-08-13

**Observed Behavior**:
Executed a controlled benchmark (`benchmarks/ne_013_authoritative_boundary.py`) comparing LLM conversational self-reflection against `AuthoritativeEvidenceQuery` (`memory/authoritative_query.py`) after reading `README.md` (which documents "32/32 tests passed"):
1. **Model Conversational Response**: Conflated claims = **True**. The model claimed 32/32 tests passed and cold boot time was verified in *this session* merely from reading file text.
2. **AuthoritativeEvidenceQuery Response**: Clean = **True**. Returned strictly `OBSERVED` tool execution events (`Tool 'read_file' executed successfully`), completely excluding unexecuted file claims.

**Evidence**:
- Artifact: `benchmarks/ne_013_authoritative_boundary_20260813_093745.json`.
- Unit tests: `tests/test_ne_013_authoritative_query.py` (3/3 PASS).
- Full regression suite: **89/89 PASS (100%)**.

**Interpretation**:
- Establishes a fundamental Guide Dog architectural boundary: **epistemic provenance queries must be answered deterministically from FlightRecorder/EvidenceStore events**.
- Models cannot be trusted to self-reflect on session verification state because they naturally conflate `DOCUMENTED` text with `OBSERVED` execution.
- `FlightConsole` remains strictly locked (`NE-010.2`).

**Bounded Claim**:
> **NE-012.3 — Target Identity Binding Validated (FROZEN 🔒):** Pre-invocation target identity validation prevents model fallback target substitution (such as root `/` or `.`), establishing that target identity is authoritative once established from the user's requested operation.

---

## 🧪 NE-014 — Intent / Input Command Boundary Diagnostic

**Date**: 2026-08-13

**Observed Behavior**:
Executed a diagnostic benchmark (`benchmarks/ne_014_intent_input_boundary.py`) analyzing input classification prior to REPL dispatch and LLM inference:
1. **Case X1 (`read files inside /docs and suggest a plan`)**: Replicated input boundary parser failure 🔴. The naive REPL string prefix check `user_input.lower().startswith("read ")` hijacked the input, slicing `"files inside /docs and suggest a plan"` and attempting literal `ReadFileTool` execution before intent classification or target grounding could run.
2. **Case X2 (`/workspace/Projects/retails`)**: Confirmed path input classification 🟢. Literal absolute paths can be parsed deterministically prior to LLM routing.

**Evidence**:
- Artifact: `benchmarks/ne_014_intent_input_boundary_2026-08-13_095223.json`.
- Full regression suite: **93/93 PASS (100%)**.

**Interpretation**:
- Proves that the input boundary failure occurs **upstream** of target grounding and model execution. Naive command string matching in REPL command loops intercepts compound natural-language inputs before intent extraction or target grounding can evaluate them.
- All previously frozen layers (`NE-009.2`, `NE-010.2`, `NE-012.1`, `NE-012.3`, `NE-013`) remain strictly locked 🔒.

**Bounded Claim**:
> **NE-014 — Input Boundary Parser Hijack Confirmed:** Naive command string matching at the input boundary hijacks compound natural language requests before target identity or LLM intent resolution can process them, demonstrating the necessity of deterministic input classification upstream of tool routing.

---

## 🧪 NE-014.1 — Input Boundary Classifier

**Date**: 2026-08-13

**Observed Behavior**:
Created and validated `InputBoundaryClassifier` (`cli/input_classifier.py`) to categorize user inputs into `DIRECT_COMMAND`, `PATH_INPUT`, and `NATURAL_LANGUAGE`:
1. **Compound Prose Protection**: `read files inside /docs and suggest a plan` is classified as `NATURAL_LANGUAGE` rather than triggering naive `read ` prefix slicing.
2. **Explicit Path Routing**: `/workspace/Projects/retails` is classified as `PATH_INPUT` for deterministic navigation/inspection.
3. **Command Preservation**: `read BOOT.md` and `doctor` remain classified as `DIRECT_COMMAND`.

**Evidence**:
- Artifact: `benchmarks/ne_014_1_input_classifier_2026-08-13_095757.json`.
- Unit tests: `tests/test_ne_014_1_input_classifier.py` (4/4 PASS).
- Full regression suite: **97/97 PASS (100%)**.

**Interpretation**:
- Demonstrates that a lightweight input-boundary classifier upstream of the REPL and LLM router eliminates literal command prefix hijacking while preserving direct CLI shortcuts.
- `FlightConsole` and all previously frozen layers remain strictly locked 🔒.

**Bounded Claim**:
> **NE-014.1 — Upstream Input Classification Validated (FROZEN 🔒):** Deterministic classification of raw inputs into DIRECT_COMMAND, PATH_INPUT, and NATURAL_LANGUAGE upstream prevents REPL string prefix hijacking and routes compound requests cleanly to LLM planning.

---

## 🧪 NE-014.2 — Live REPL Routing Integration

**Date**: 2026-08-13

**Observed Behavior**:
Evaluated live REPL command loop routing (`cli/repl.py`) with integrated `InputBoundaryClassifier`:
1. **Case R1 (`read BOOT.md`)**: Routed to `DIRECT_COMMAND`, executing `ReadFileTool` directly without LLM latency.
2. **Case R2 (`read files inside /docs and suggest a plan`)**: Routed to `NATURAL_LANGUAGE`, passing full request context to LLM planning with **zero** literal read hijack.
3. **Case R3 (`/workspace/Projects/retails`)**: Routed to `PATH_INPUT`, performing deterministic directory listing without LLM inference.

**Evidence**:
- Artifact: `benchmarks/ne_014_2_live_routing_20260813_111426.json`.
- Full regression suite: **97/97 PASS (100%)**.

**Interpretation**:
- Confirms that input boundary classification is active on live REPL traffic, eliminating input prefix hijacking while preserving fast deterministic CLI shortcuts.
- All layers (`NE-009.2`, `NE-010.2`, `NE-012.1`, `NE-012.3`, `NE-013`, `NE-014.1`, `NE-014.2`) are strictly locked 🔒.

**Bounded Claim**:
> **NE-014.2 — Live Input Boundary Routing Validated (FROZEN 🔒):** Live REPL integration proves that upstream input classification eliminates command prefix hijacks on natural language prompts while retaining zero-latency deterministic execution for direct paths and CLI commands.

---

## 🧪 NE-015 — Multi-Step Governed Execution Diagnostic Baseline

**Date**: 2026-08-13

**Observed Behavior**:
Evaluated multi-step prompt execution ("Read the files inside /docs before we do anything and suggest a solid plan.") against the frozen execution stack (`benchmarks/ne_015_multistep_governed.py`):
1. **Ingress Input Routing (NE-014.2)**: Prompt classified cleanly as `NATURAL_LANGUAGE` 🟢 (bypassed REPL prefix hijacking).
2. **Model Operation Selection**: Model attempted `read_file(path="/docs")` ⚠️. TargetResolver returned file not found, and `EvidenceStore` recorded 0 `OBSERVED` events and 1 `UNVERIFIED` event.
3. **Plan Synthesis**: Model synthesized a structured plan acknowledging that `/docs` was missing without inventing false execution evidence.

**Evidence**:
- Artifact: `benchmarks/ne_015_multistep_governed_20260813_111804.json`.
- Trace: `benchmarks/ne015_multistep_governed_20260813_111804.jsonl`.
- Full regression suite: **97/97 PASS (100%)**.

**Interpretation**:
- Confirms that frozen execution layers (`NE-014`, `NE-012.1`, `NE-013`) protect the runtime during multi-step natural language execution.
- Establishes the exact research boundary for **NE-015.1**: decomposing multi-step intents into structured tool sequences prior to raw tool dispatch.

**Bounded Claim**:
> **NE-015 — Multi-Step Governed Execution Baseline Established:** Multi-step prompts pass ingress classification intact, and downstream frozen guards enforce evidence isolation when model tool selection encounters missing targets.

---

## 🧪 NE-016 — Governed Plan Execution Diagnostic Baseline

**Date**: 2026-08-13

**Observed Behavior**:
Evaluated governed plan execution (`benchmarks/ne_016_governed_plan.py`) where multi-step plans are submitted to the L.I.S.A. Kernel for step-by-step validation and execution:
1. **Valid Plan Transition**: Plan 1 (`list_directory(".")` $\rightarrow$ `read_file("README.md")`) executed sequentially under kernel validation, producing 2 `OBSERVED` trace events.
2. **Rejection & Execution Halting**: Plan 2 (`list_directory("README.md")` $\rightarrow$ `read_file("README.md")`) triggered kernel rejection on Step 1 (`list_directory` on `FILE` target). The kernel halted execution immediately, leaving Step 2 in `PENDING` state and preventing downstream ungrounded tool calls.

**Evidence**:
- Artifact: `benchmarks/ne_016_governed_plan_20260813_114659.json`.
- Trace: `benchmarks/ne016_governed_plan_20260813_114659.jsonl`.
- Unit tests: `tests/test_ne_016_governed_plan.py` (1/1 PASS).
- Full regression suite: **98/98 PASS (100%)**.

**Interpretation**:
- Establishes that the L.I.S.A. Kernel can govern multi-step plan execution independently of the LLM compute driver.
- Validates the separation of **Driver State** (proposed plan), **Capability State** (executed tools), and **Kernel State** (validated transitions and recorded trace evidence).

**Bounded Claim**:
> **NE-016 — Governed Plan Execution Validated (FROZEN 🔒):** Multi-step plans executed under kernel supervision validate target identity and type grounding per step, halting downstream execution on step failure and deriving authoritative evidence from recorded execution events.

---

## 🧪 NE-016.1 — Plan Recovery & Replanning Baseline

**Date**: 2026-08-13

**Observed Behavior**:
Evaluated mid-plan execution failure and replanning recovery under kernel supervision (`benchmarks/ne_016_1_plan_recovery.py`):
1. **Plan A Execution & Halting**: Step 1 (`list_directory(".")`) succeeded (`EXECUTED`), but Step 2 (`read_file("missing_docs.md")`) failed (`BLOCKED`). The kernel immediately invalidated Plan A, halting Step 3 in `PENDING` state.
2. **Revised Plan B Execution**: The driver proposed revised Plan B (`read README.md` $\rightarrow$ `list tools`), which the kernel validated and executed to completion (`EXECUTED`).
3. **Immutable Provenance**: `AuthoritativeEvidenceQuery` verified **3 `OBSERVED` events** and **1 `UNVERIFIED` event**, confirming that Plan B execution appended to the trace without modifying Plan A's failure evidence.

**Evidence**:
- Artifact: `benchmarks/ne_016_1_plan_recovery_20260813_114856.json`.
- Trace: `benchmarks/ne016_1_plan_recovery_20260813_114856.jsonl`.
- Unit tests: `tests/test_ne_016_1_plan_recovery.py` (1/1 PASS).
- Full regression suite: **99/99 PASS (100%)**.

**Interpretation**:
- Validates the **Plan Recovery Law**: A failed plan step invalidates downstream assumptions; subsequent execution requires kernel validation of a revised plan while preserving immutable recorded trace evidence.

**Bounded Claim**:
> **NE-016.1 — Plan Recovery Law Validated (FROZEN 🔒):** Mid-plan step failure invalidates downstream plan execution and transitions kernel state to BLOCKED, enabling driver replanning while maintaining immutable recorded trace evidence across plan revisions.

---

## 🧪 NE-017 — Real-Project L.I.S.A. OS End-to-End Validation

**Date**: 2026-08-13

**Observed Behavior**:
Executed end-to-end system validation benchmark (`benchmarks/ne_017_real_project_validation.py`) on real external project `/home/user/development/projects/retails`:
1. **Ingress Boundary Routing**: Complex multi-part prompt classified as `NATURAL_LANGUAGE` (`ingress_clean = True`), passing context to model planning intact.
2. **Capability Tool Execution**: Model issued 3 valid `list_directory` calls across workspace directories, which executed and ingested into `OBSERVED` evidence.
3. **Target Grounding & Fact Conflation**: Attempted read of non-existent file (`docs/project_directives.conf`) failed safely. Model response acknowledged missing target without inventing false execution claims (`conflation_detected = False`).
4. **Authoritative Evidence Derivation**: `AuthoritativeEvidenceQuery` verified **3 `OBSERVED` events** and **1 `UNVERIFIED` event**.

**Evidence**:
- Artifact: `benchmarks/ne_017_real_project_validation_20260813_120154.json`.
- Trace: `benchmarks/ne017_real_project_validation_20260813_120154.jsonl`.
- Full regression suite: **99/99 PASS (100%)**.

**Interpretation**:
- Confirms that the L.I.S.A. Intelligence Operating System (v2.0.0) operates coherently end-to-end on real, un-mocked engineering repositories while strictly enforcing all kernel laws and evidence safeguards.

**Bounded Claim**:
> **NE-017 — Real-Project L.I.S.A. OS Validation Validated (FROZEN 🔒):** End-to-end execution on real engineering repositories validates that L.I.S.A. OS governs ingress classification, resource grounding, capability execution, and authoritative evidence derivation without fact conflation or regression.

---

## 🧪 NE-018 — Research Before Implementation Diagnostic Baseline

**Date**: 2026-08-13

**Observed Behavior**:
Evaluated the kernel `ResearchGate` on unfamiliar project `/home/user/development/projects/retails` (`benchmarks/ne_018_research_gate.py`):
1. **Knowledge Scoring & Mode Enforcement**: Knowledge score evaluated to 1/3 (`is_sufficient = False`), cleanly enforcing `RESEARCH_MODE`.
2. **Implementation Gate Interception**: Attempted `write_file` tool call in `RESEARCH_MODE` was deterministically blocked (`gate_blocked_initially = True`).
3. **Research & Knowledge Checkpoint**: Read-only discovery inspected workspace structure and generated `NE018_PROJECT_CONTEXT.md` knowledge checkpoint artifact.
4. **Mode Promotion**: Post-checkpoint, session mode promoted to `IMPLEMENTATION_MODE`, permitting `write_file` capability execution (`post_checkpoint_allowed = True`).

**Evidence**:
- Artifact: `benchmarks/ne_018_research_gate_20260813_120658.json`.
- Trace: `benchmarks/ne018_research_gate_20260813_120658.jsonl`.
- Unit tests: `tests/test_ne_018_research_gate.py` (4/4 PASS).
- Full regression suite: **103/103 PASS (100%)**.

**Interpretation**:
- Validates the **Research Gate Law**: *L.I.S.A. must establish sufficient authoritative project knowledge before permitting implementation on an unfamiliar or insufficiently documented project.*

**Bounded Claim**:
> **NE-018 — Research Gate Law Validated (FROZEN 🔒):** Insufficient project knowledge score enforces RESEARCH_MODE and blocks implementation tool dispatch prior to Knowledge Checkpoint completion, promoting to IMPLEMENTATION_MODE only after authoritative context documentation is established.

---

## 🧪 NE-018.1 — Knowledge Checkpoint Integrity Baseline

**Date**: 2026-08-13

**Observed Behavior**:
Evaluated `KnowledgeCheckpointVerifier` across superficial and authoritative checkpoint candidates (`benchmarks/ne_018_1_checkpoint_integrity.py`):
1. **Superficial Checkpoint Interception**: Checkpoint candidate lacking trace evidence for required domains scored 0.0, halting mode promotion and retaining session state in `RESEARCH_MODE`.
2. **Authoritative Checkpoint Verification**: Checkpoint candidate with 10/10 required domains backed by `OBSERVED` trace sources (`list_directory('.')`, `read_file('pubspec.yaml')`, `read_file('AGENTS.md')`) scored 1.0, cleanly authorizing promotion to `IMPLEMENTATION_MODE`.

**Evidence**:
- Artifact: `benchmarks/ne_018_1_checkpoint_integrity_20260813_120850.json`.
- Trace: `benchmarks/ne018_1_checkpoint_integrity_20260813_120850.jsonl`.
- Unit tests: `tests/test_ne_018_1_checkpoint_integrity.py` (2/2 PASS).
- Full regression suite: **105/105 PASS (100%)**.

**Interpretation**:
- Validates the **Knowledge Integrity Law**: *A Knowledge Checkpoint may authorize implementation only when its required project knowledge is supported by authoritative evidence from the inspected project.*

**Bounded Claim**:
> **NE-018.1 — Knowledge Integrity Law Validated (FROZEN 🔒):** Knowledge Checkpoint verification requires trace-backed OBSERVED evidence across required project knowledge domains, rejecting superficial prose claims and preventing unauthorized promotion to IMPLEMENTATION_MODE.

---

## 🧪 NE-019 — Autonomous Project Boot & Environment Discovery Baseline

**Date**: 2026-08-13

**Observed Behavior**:
Evaluated `AutonomousProjectBootEngine` on unfamiliar project `/home/user/development/projects/retails` (`benchmarks/ne_019_autonomous_boot.py`):
1. **Autonomous Exploration**: Boot engine detected `RESEARCH_MODE`, executing capability exploration (`list_directory('.')` and `read_file` across key configuration manifests) without human prompting.
2. **Domain Fact Mapping**: Mapped findings into 10 required knowledge domains backed by `OBSERVED` trace events.
3. **Checkpoint Verification & Promotion**: `KnowledgeCheckpointVerifier` scored integrity at **1.0**, authorizing promotion to `IMPLEMENTATION_MODE`.

**Evidence**:
- Artifact: `benchmarks/ne_019_autonomous_boot_20260813_121307.json`.
- Trace: `benchmarks/ne019_autonomous_boot_20260813_121307.jsonl`.
- Unit tests: `tests/test_ne_019_autonomous_boot.py` (1/1 PASS).
- Full regression suite: **106/106 PASS (100%)**.

**Interpretation**:
- Demonstrates that L.I.S.A. Intelligence OS (v2.0.0) can autonomously boot unfamiliar repositories, explore their environment, build trace-backed knowledge checkpoints, and promote operating context before allowing workloads to execute.

**Bounded Claim**:
> **NE-019 — Autonomous Project Boot Validated (FROZEN 🔒):** The Autonomous Boot Engine autonomously explores unfamiliar workspaces, maps trace evidence to 10 required knowledge domains, and establishes authoritative checkpoints to promote session state to IMPLEMENTATION_MODE.

---

## 🧪 NE-018.2 — Question-Driven Research & Investigation Integrity Baseline

**Date**: 2026-08-13

**Observed Behavior**:
Evaluated `QuestionDrivenInvestigationEngine` (`benchmarks/ne_018_2_investigation_integrity.py`):
1. **Question Framing & Investigation**: Posed explicit domain questions (`Q-001` .. `Q-004`) and investigated them using read-only capability tools.
2. **Difficulty Detection & Resolution**: Detected persistence ambiguity (`D-001`: Hive documentation vs Drift manifest code). Resolved difficulty via active call graph inspection and recorded resolution provenance.
3. **Traceability Checkpoint**: Kernel verified that all questions and difficulties were resolved or explicitly tracked with risk bounds, authorizing promotion to `IMPLEMENTATION_MODE`.

**Evidence**:
- Artifact: `benchmarks/ne_018_2_investigation_integrity_20260813_121457.json`.
- Trace: `benchmarks/ne018_2_investigation_integrity_20260813_121457.jsonl`.
- Unit tests: `tests/test_ne_018_2_investigation_integrity.py` (1/1 PASS).
- Full regression suite: **107/107 PASS (100%)**.

**Interpretation**:
- Validates the **Investigation Integrity Law**: *L.I.S.A. must investigate before implementing. An investigation begins with questions, not assumptions. Every significant discovery, uncertainty, contradiction, failed approach, and difficulty encountered during research must be recorded and incorporated into the project's knowledge documentation.*

**Bounded Claim**:
> **NE-018.2 — Investigation Integrity Law Validated (FROZEN 🔒):** Question-driven research tracks explicit question resolution and difficulty provenance, ensuring that contradictions and uncertainties are recorded and resolved prior to authorizing IMPLEMENTATION_MODE.




















