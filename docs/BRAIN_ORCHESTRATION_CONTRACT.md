# BOE-01 — Brain Orchestration Engine Contract

**Status:** Proposed subsystem contract — review required  
**Version:** 0.1.0  
**Scope:** Provider-neutral registration, task suitability, dispatch, handoff, and result reconciliation  
**Authority:** Subordinate to existing L.I.S.A. kernel laws L1–L7  
**Implementation status:** Specification only; no runtime capability is claimed.

## 1. Purpose

The Brain Orchestration Engine (BOE) coordinates interchangeable reasoning resources so work can continue across models, providers, authorized accounts, and local inference runtimes.

BOE is not a model-ranking leaderboard or a thin API router. It matches tasks to suitable authorized resources, supplies bounded work packages, preserves continuity, and returns results for kernel-governed evaluation.

> The model supplies reasoning. BOE coordinates the work. The kernel retains authority.

L.I.S.A. must improve system-level capability without requiring every connected model to be independently powerful.

## 2. Non-negotiable invariants

1. **Kernel supremacy:** BOE cannot grant permissions, change project identity, authorize writes, or declare execution truth.
2. **Provider neutrality:** Core contracts contain no provider-specific request or response objects.
3. **Evidence provenance:** Capability, availability, quota, and performance claims carry a source and observation time.
4. **Unknown is valid:** Missing or stale information remains UNKNOWN; it is never silently guessed.
5. **Task continuity:** A task is independent of any one model call, provider session, or conversation.
6. **Scoped context:** Every task and context package is bound to an explicit project/workspace scope.
7. **No quota evasion:** Scheduling respects provider terms, limits, and account authorization.
8. **Governed execution:** Model output is a proposal. Existing approval, audit, rollback, and validation gates remain authoritative.
9. **Safe concurrency:** Dependencies are enforced and conflicting writes are serialized or rejected.
10. **Explainable selection:** Every dispatch records why a resource was selected and which constraints excluded alternatives.

## 3. Responsibility boundaries

| Component | Responsibility | Must not own |
|---|---|---|
| Brain Registry | Stable identities and authorized connection metadata | Secrets or kernel permissions |
| Capability Profile | Declared and observed task-relevant capabilities | Unverified claims presented as facts |
| Availability / Quota Observer | Timestamped resource observations | Provider limit circumvention |
| Suitability Evaluator | Deterministic eligibility and explainable ranking | Final authority over task safety |
| Task Orchestrator | Decomposition, dependencies, ownership, dispatch lifecycle | Project authorization |
| Context Assembler | Scoped retrieval and bounded work packages | Source-of-truth status for summaries |
| Handoff Manager | Checkpoints and provider-independent continuation | Transcript as sole memory |
| Result Reconciler | Compare outputs, expose conflict, request evidence | Majority vote as proof |
| Provider Adapter | Translate neutral contracts to provider APIs | Kernel state or policy decisions |
| Kernel / Governance | Identity, policy, authorization, evidence, execution control | Provider-specific reasoning |

## 4. Core data contracts

The following are conceptual typed records. Concrete language, serialization, and storage choices are intentionally deferred.

### 4.1 BrainDescriptor

Represents one authorized reasoning resource.

Required fields:
- brain_id: stable L.I.S.A.-assigned identifier.
- provider_id: provider or runtime identifier.
- model_id: model/runtime identifier as reported by the adapter.
- adapter_id: adapter contract and version.
- resource_kind: hosted API, local runtime, or another supported execution class.
- authorization_ref: reference to secure authorization; never a token or secret.
- status: enabled, disabled, or quarantined.
- created_at and updated_at.

Optional descriptive fields include supported modalities, interface features, context/input/output constraints with provenance, and operator labels.

A display name is not an identity. Provider model names may change; L.I.S.A.'s stable brain_id must not.

### 4.2 CapabilityObservation

A capability is a task-relevant assertion, not a vague intelligence score.

Fields:
- brain_id and capability.
- level: supported, unsupported, or unknown; optional measured range where meaningful.
- evidence_kind: provider declaration, operator declaration, benchmark, or observed task outcome.
- evidence_ref where available.
- observed_at and optional expires_at.
- constraints and workload conditions.

Declared capability and empirically observed suitability must remain distinguishable. A benchmark is evidence for a defined workload, not a universal intelligence rating.

### 4.3 ResourceState

Availability and quota are independent dimensions.

- availability: available, degraded, unavailable, or unknown.
- quota_state: available, limited, exhausted, or unknown.
- observed_at and source.
- optional provider-reported reset_at and retry_after.
- scope: the resource/account/model scope to which the observation applies.

Stale observations become unknown according to an explicit freshness policy. BOE must not infer reset times or invent remaining quota.

### 4.4 TaskRequest

Every task must be independently understandable and evaluable.

Required fields:
- task_id and objective.
- project_scope and task_class.
- required_capabilities and acceptance_criteria.
- context_budget and sensitivity_class.
- execution_mode: reasoning-only, read-only tool work, or governed mutation proposal.
- dependencies.
- created_by and created_at.

Optional fields include preferred/forbidden brains or providers, deadline, latency preference, cost ceiling, required modalities, artifact/evidence references, and operator priority.

A task with unresolved project identity, missing authorization scope, or undefined acceptance criteria must not be dispatched as executable work.

### 4.5 DispatchDecision

A deterministic, auditable decision record containing:
- task_id and selected_brain_id, if any.
- eligible_candidates.
- excluded_candidates with reason codes.
- selection_factors and their observed inputs.
- policy_constraints_applied.
- decision_at and fallback_policy.

No eligible resource is a valid outcome. BOE must return NO_ELIGIBLE_BRAIN rather than silently weakening task requirements.

### 4.6 HandoffPackage

A provider-independent continuation unit containing:
- Objective and task identifier.
- Project scope and relevant source/evidence references.
- Accepted facts with provenance.
- Decisions and rationale.
- Hypotheses clearly labelled as hypotheses.
- Open questions, blockers, and contradictions.
- Completed work and validation status.
- Pending actions and acceptance criteria.
- Context budget and required capabilities.
- Checkpoint version and integrity metadata.

A handoff is a compact working package, not a raw transcript dump. The receiving brain must be told what it has and has not actually been given.

### 4.7 BrainResult

A normalized result envelope containing:
- task_id, brain_id, and dispatch_id.
- result_status: completed, partial, refused, failed, or timed out.
- output_refs.
- claims with evidence references or explicit unsupported status.
- assumptions, uncertainties, and unresolved_questions.
- tool_requests, which remain proposals until authorized execution.
- usage_metadata where provider-reported.
- started_at and completed_at.

A provider response saying a tool ran is not proof that it ran. Actual execution must be observed and recorded by the capability and FlightRecorder path.

## 5. Task lifecycle

~~~text
CREATED
   |
   v
VALIDATING -----> BLOCKED
   |
   v
READY
   |
   v
SELECTING ------> NO_ELIGIBLE_BRAIN
   |
   v
DISPATCHED
   |
   v
RUNNING
   |----> PARTIAL
   |----> COMPLETED
   |----> FAILED
   |----> TIMED_OUT
   |----> REFUSED
   |
   v
RECONCILING
   |----> NEEDS_EVIDENCE
   |----> NEEDS_OPERATOR
   |----> ACCEPTED
   |----> REJECTED
~~~

A task may be re-queued or handed off after failure, timeout, refusal, or provider unavailability. The prior attempt remains immutable evidence; retries create new attempt records.

Only the kernel-governed task state machine may mark work accepted. A model cannot mark its own output accepted.

## 6. Brain selection policy

Selection occurs in two stages.

### Stage A — hard eligibility

A candidate is eligible only if:
- It is registered, enabled, and authorized for the task scope.
- Its adapter supports the required interaction mode.
- Required modalities and capabilities are supported or explicitly allowed as uncertain.
- Availability is not known to be unavailable.
- Quota is not known to be exhausted.
- Context and output constraints can be satisfied.
- Data sensitivity and provider policy permit the task.
- Operator constraints and project policy are satisfied.

Unknown facts must be handled according to explicit policy. For sensitive tasks, unknown data-handling terms or authorization must exclude the candidate.

### Stage B — explainable suitability

Eligible candidates may be compared using task-specific factors:
- Evidence-backed capability suitability.
- Context fit.
- Observed reliability on comparable tasks.
- Availability and expected latency.
- Cost, when known and relevant.
- Operator preference.

No universal scalar intelligence score is required. The evaluator exposes factor values and rationale. Missing measurements must not be fabricated or treated as zero-cost/perfect performance.

The initial implementation should use deterministic rules and transparent weighting. Learned routing may be considered later only with evaluation data, drift monitoring, and operator-visible explanations.

## 7. Decomposition and concurrency

Task decomposition must produce a dependency graph. Each child task needs a defined objective, input/output artifacts, acceptance criteria, required capabilities, sensitivity, dependencies, and write/conflict classification.

Independent read-only tasks may run concurrently. Tasks that can mutate the same project or shared resource require serialization, an explicit lock/coordination protocol, or rejection.

Parallelism is an optimization, not a correctness requirement. A sequential plan is preferred whenever dependencies, shared state, or uncertainty make concurrency unsafe.

## 8. Context and project knowledge

The Context Engine retrieves only material relevant to the task and within its context budget.

Every included item should retain:
- Project identity and source path or stable source reference.
- Content hash or version.
- Retrieval timestamp.
- Provenance class: observed, documented, operator-provided, or model-generated.
- Relevance reason.

Summaries are derived artifacts. They link to source evidence and must be invalidated or rechecked when source versions change.

Cross-project retrieval is denied by default. Explicitly authorized shared knowledge must be labelled and must not expose project-private material.

## 9. Handoff and interruption recovery

When a brain becomes unavailable or a session ends:
1. Persist the current task attempt and last durable checkpoint.
2. Preserve completed outputs and evidence references.
3. Record what was in progress and what is uncertain.
4. Re-evaluate resource eligibility.
5. Build a new handoff package for the replacement brain.
6. Start a new attempt linked to the prior attempt.
7. Reconcile the new result with previous work; do not discard or silently overwrite it.

A handoff must never claim that the replacement brain remembers the previous conversation. It receives only the package and explicitly attached context.

## 10. Result reconciliation

Reconciliation must separate factual claims, interpretations, recommendations, and generated artifacts; compare outputs; identify agreement, disagreement, omissions, and unsupported assertions; preserve provenance; seek source evidence or deterministic checks for material conflicts; and keep unresolved conflicts open.

Majority voting is not proof. For high-impact or mutating work, policy may require independent review. The reviewer must receive sufficient evidence to evaluate the result, not merely another model's conclusion.

## 11. Failure and fallback rules

| Condition | Required behavior |
|---|---|
| Provider unavailable | Preserve checkpoint; retry only under explicit policy or select eligible alternative |
| Quota exhausted | Record source; do not bypass limits |
| Quota unknown | Apply task sensitivity policy; do not assume availability |
| Context overflow | Rebuild a smaller evidence-linked package or decompose task |
| Adapter error | Record normalized failure; do not corrupt task state |
| Model refusal | Preserve refusal; do not automatically route around safety restrictions |
| Conflicting outputs | Mark conflict and seek evidence |
| No eligible brain | Keep task queued/blocked with explicit reason |
| Interrupted dispatch | Reconcile attempt state before retrying; avoid duplicate side effects |
| Invalid/stale handoff | Reject or rebuild from authoritative sources |

Retries must be bounded, idempotency-aware, and visible in task history.

## 12. Security and privacy

- Credentials live only in secure provider-specific secret storage.
- Task records, indexes, prompts, logs, and handoffs contain credential references at most, never secret values.
- Provider data-retention and training policies are represented as policy inputs where known.
- Sensitive data is not sent to a provider unless explicitly authorized.
- Project scope is checked before retrieval and again before dispatch.
- Tool permissions are issued by the kernel, not inferred from model intent.
- Provider adapters are treated as untrusted integration boundaries.
- Audit records must not leak prompt secrets or private project content unnecessarily.

## 13. Initial implementation sequence

BOE must be delivered incrementally. The first implementation must not begin with autonomous multi-agent code modification.

| Stage | Scope | Exit condition |
|---|---|---|
| BOE-01 | Contract and invariants | Reviewed, internally consistent provider-neutral specification |
| BOE-02 | Read-only Brain Registry | Register/list/inspect resources without storing secrets |
| BOE-03 | Capability and Resource Observations | Provenance, freshness, and unknown states tested |
| BOE-04 | Deterministic Suitability Evaluator | Explainable decisions and no-eligible outcomes |
| BOE-05 | Task/Handoff persistence | Task survives process and provider-session boundaries |
| BOE-06 | Single-brain dispatch | One governed task dispatches and returns normalized results |
| BOE-07 | Reconciliation | Conflicts and unsupported claims remain visible |
| BOE-08 | Bounded parallel read-only tasks | Dependency and concurrency safety demonstrated |
| BOE-09 | Governed tool proposals | Existing authorization, audit, rollback, and validation gates preserved |

MCP, CLI, desktop, and IDE integrations are interfaces over these contracts. None owns BOE state or authority.

## 14. BOE-01 acceptance checklist

- [ ] Existing L1–L7 laws remain unchanged.
- [ ] Provider-specific details are isolated behind adapters.
- [ ] Resource identity is stable and secrets are excluded.
- [ ] Capability and availability assertions have provenance and freshness.
- [ ] Unknown states are represented explicitly.
- [ ] Task contracts include scope, sensitivity, dependencies, and acceptance criteria.
- [ ] Selection has hard eligibility gates and explainable suitability.
- [ ] Handoffs distinguish facts, decisions, hypotheses, and unknowns.
- [ ] Retries preserve attempt history and account for side effects.
- [ ] Parallel work has dependency and write-conflict controls.
- [ ] Model output cannot authorize execution or declare evidence.
- [ ] The specification makes no claim of runtime implementation.

---

**Design rule:** BOE does not ask, “Which model is the smartest?” It asks, “Which authorized reasoning resource is suitable for this task, with this context, under these constraints — and how will L.I.S.A. know whether the result is trustworthy?”


## 15. Existing repository mapping and migration notes

A read-only inspection of the current provider implementation identified an existing foundation. BOE should extend these contracts rather than create a parallel provider stack.

### Existing components observed

| Existing component | Observed responsibility | BOE relationship |
|---|---|---|
| providers/base.py | BaseProvider, ChatRequest, ChatResponse | Retain as provider-adapter boundary; evolve normalized metadata carefully |
| providers/manifest.py | ProviderManifest with provider id, health, priority, capabilities, model list, configuration, limits, metadata | Preserve compatibility while adding evidence-backed model/resource profiles |
| providers/registry.py | In-memory provider and manifest registration; handshake and duplicate checks | Evolve as provider adapter registry, not the complete brain/account registry |
| providers/selector.py | Exact capability matching, healthy flag, numeric priority | Replace/augment with hard eligibility plus explainable task suitability |
| engine/auto_selector.py | Prompt analysis, model-tier string heuristics, provider selection | Integrate with BOE task contracts; remove silent requirement relaxation |
| core/context.py | Provider capability enum and session context | Reuse capability vocabulary where semantically correct; do not confuse provider capability with model-specific capability |

### Verified gaps and risks

1. **Provider identity is not brain identity.** Current registry keys one provider instance by provider id. It does not separately represent multiple models, authorized accounts, endpoints, or local runtime instances under one provider.
2. **Registry state is process-local.** The current registry uses in-memory dictionaries. It is not a persistent, versioned resource inventory.
3. **Manifest evidence is thin.** Capability declarations and healthy status have no explicit provenance, observation timestamp, freshness, or confidence.
4. **Selection is coarse.** ProviderSelector checks a healthy boolean and exact capability membership, then sorts by provider priority. It does not evaluate task sensitivity, model context limits, quota, cost, latency, or observed task performance.
5. **Model choice is heuristic.** AutoSelector selects models using name fragments such as large, 70b, pro, mini, flash, and 3b. These are hints, not reliable capability evidence.
6. **Requirements can be weakened.** AutoSelector catches broad exceptions and retries selection using CHAT. This can conceal the actual selection failure and may dispatch a task without its original required capabilities. BOE integration must remove this behavior or make fallback an explicit, policy-approved task transformation with operator-visible rationale.
7. **Provider adapter behavior differs in maturity.** The current OpenAI adapter is a placeholder: it defaults to a mock key, reports healthy without a live check, and returns a synthetic response. It must not be treated as a verified live provider connection or source of real capability/availability evidence.
8. **Blocking I/O exists in the Ollama adapter.** Its async methods call synchronous urllib operations. This is a reliability/latency concern for concurrent orchestration and should be addressed before relying on high-concurrency dispatch.
9. **Existing tests cover basic selection, not BOE guarantees.** Current provider tests exercise registration, health rejection, capability matching, and basic AutoSelector behavior. They do not yet establish persistence, provenance freshness, quota handling, model/account separation, safe handoff, explainable selection, or concurrency isolation.

These observations are a source-code inspection, not a runtime test report. No provider was contacted and no tests were run as part of this documentation update.

### Recommended migration order

1. Keep BaseProvider and ProviderRegistry as the adapter foundation.
2. Introduce a separate Brain/Resource descriptor that references a provider adapter and identifies a concrete model/runtime/account resource without storing credentials.
3. Add versioned persistent resource metadata and timestamped observations; preserve the current registry API through a compatibility layer where practical.
4. Add a deterministic suitability evaluator that never silently drops required capabilities.
5. Make model-specific capability/context observations distinct from provider-level interface capabilities.
6. Replace name-fragment model selection with explicit profiles and evidence-backed observations; retain name heuristics only as low-confidence hints.
7. Implement task and handoff persistence before multi-brain parallel dispatch.
8. Treat live provider connectivity and adapter conformance as separate from declared manifests. Mock adapters must be explicitly labelled as test fixtures.

Do not start BOE-02 by rewriting every provider. First define the compatibility seam between the existing ProviderRegistry and the new Brain Registry, then add contract tests for that seam.
