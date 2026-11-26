# 🧠 L.I.S.A. — Intelligence Operating System (v2.1.0)

```
===================================================
L.I.S.A. INTELLIGENCE OPERATING SYSTEM
===================================================

Version          : v2.1.0
NE Baseline      : FROZEN — L1–L7 / NE-009.2 → NE-019
NE Baseline Audit: 2026-08-13
NE Baseline Tests : 107/107 PASS

===================================================
```

> The NE baseline is the frozen foundation. Subsequent capabilities, including Cross-Project Intelligence, are developed incrementally and validated on their own branches and CI workflows.

---

## 🏛️ What is L.I.S.A.?

**L.I.S.A.** is an **Intelligence Operating System** — not another AI assistant or a wrapper around one model.

> *"L.I.S.A. is an operating environment that governs reasoning drivers and capability providers while maintaining authoritative state and evidence."*

L.I.S.A. sits between the **operator**, connected reasoning providers, and capability tools. It supplies the persistent context, knowledge, coordination, governance, and evidence that allow different models and tools to contribute to continuous work without becoming the authority over the system.

**The brain is replaceable. The intelligence infrastructure is persistent.**

A model may reason, plan, or propose work. L.I.S.A. retains project identity, task continuity, authoritative state, permissions, and execution evidence.

```text
                         👤 OPERATOR
                              │
                              ▼
              ┌───────────────────────────────┐
              │           L.I.S.A. OS         │
              │                               │
              │  Kernel / Governance          │
              │  Research & Planning          │
              │  Context & Knowledge         │
              │  Brain Orchestration          │
              │  Evidence & Execution         │
              └───────────────┬───────────────┘
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        🤖 BRAIN A       🤖 BRAIN B       🤖 LOCAL MODEL
        reasoning        reasoning        reasoning
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                     🧰 CAPABILITIES
                  tools / projects / services
                              │
                              ▼
                        REAL WORLD
                              │
                              ▼
                       📼 FLIGHT RECORDER
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
          AUTHORITATIVE                OPERATOR
             EVIDENCE                     VIEW
```

The diagram describes the intended operating model. Multi-brain orchestration and the supporting resource managers are architectural direction, not a claim that every capability is already implemented.

### Founding philosophy

L.I.S.A. is intended to reduce dependence on any single model's context window, capabilities, quota, account, or conversation lifetime.

- **Model independence:** providers are interchangeable reasoning resources.
- **Context continuity:** project knowledge and task state persist outside individual conversations.
- **Capability augmentation:** retrieval, tools, planning, and governance strengthen what each model can accomplish.
- **Multi-brain coordination:** suitable models can contribute to different tasks, including bounded parallel work.
- **Evidence-first decisions:** disagreements, unknowns, and provenance remain visible.
- **Operator authority:** models propose; L.I.S.A. governs; the operator retains control over consequential actions.

Read the [L.I.S.A. Founding Philosophy](docs/FOUNDING_PHILOSOPHY.md) for the principles and safety boundaries. The proposed [Brain Orchestration Engine Contract](docs/BRAIN_ORCHESTRATION_CONTRACT.md) translates those principles into provider-neutral contracts, task lifecycle rules, selection policy, handoff, and staged implementation criteria. BOE-01 is a specification, not an implemented runtime.

---

## ⚖️ Immutable Kernel Laws (L1–L7)

| Law | Name | Principle |
|---|---|---|
| **L1** | Untrusted Compute Driver | LLMs are interchangeable compute backends, not the OS authority |
| **L2** | Kernel Supremacy | The kernel owns state, identity, and evidence. No LLM response can redefine reality |
| **L3** | Knowledge is Capabilities | Knowledge modules are deterministic capability providers |
| **L4** | Deterministic Ingress | User inputs are classified before model routing; CLI commands bypass the model entirely |
| **L5** | Authoritative Evidence Boundary | Epistemic provenance derives from `FlightRecorder` event streams, not LLM self-reflection |
| **L6** | Zero Vendor Lock-In | All subsystems execute independently of model provider specifics |
| **L7** | **Epistemic Humility** | L.I.S.A. must not pretend to know what it has not observed. An openly-tracked unknown is valuable. A falsely-answered question is a kernel violation |

> **"A plan is a proposal, not authority."**
> **"The driver may think. The capability may act. The kernel decides what actually happened."**
> **"An investigation begins with questions, not assumptions."**

---

## 🔬 Research Subsystem

Research is a **first-class OS subsystem**, not a freeform LLM activity.

When L.I.S.A. opens an unfamiliar project, the correct internal state is:

> *"I don't know yet. What do I need to know? What evidence can answer it? What conflicts have I encountered? What remains unknown? Only when I have sufficient evidence may I proceed."*

### Research loop

```text
UNKNOWN PROJECT → RESEARCH_MODE → ASK QUESTIONS → INVESTIGATE
      → OBSERVE EVIDENCE → RECORD DISCOVERIES / CONTRADICTIONS
      → INVESTIGATE MORE → RESOLVE → DOCUMENT FINDING
      → KNOWLEDGE CHECKPOINT → INTEGRITY VALIDATION
      → IMPLEMENTATION_MODE
```

### Question lifecycle (kernel-enforced)

| State | Kernel Rule |
|---|---|
| `OPEN` | Valid — record impact + implementation restriction |
| `INVESTIGATING` | Valid — implementation tools blocked |
| `RESOLVED` | Valid — evidence source must be recorded |
| `ACCEPTED_AS_OPEN` | Valid — impact + restriction must be documented |
| `NOT_APPLICABLE` | Valid — reason must be recorded |
| `ANSWERED` (no evidence) | ❌ **Kernel violation** |

---

## 🧪 NE Benchmark Baseline

The following milestones form the frozen NE foundation (107/107 baseline tests passed at the recorded audit):

| Benchmark | Capability Proven | Status |
|---|---|---|
| **NE-010.2** | `FlightConsole` — projection-only operator view | 🔒 Frozen |
| **NE-012** | Intent grounding, `TargetInspector` stat pre-checks | 🔒 Frozen |
| **NE-012.1** | Target type grounding + `EvidenceStore` classification | 🔒 Frozen |
| **NE-012.3** | Target identity binding — no root/`.` fallback substitution | 🔒 Frozen |
| **NE-013** | `AuthoritativeEvidenceQuery` — trace truth without LLM reflection | 🔒 Frozen |
| **NE-014.1** | `InputBoundaryClassifier` — deterministic ingress routing | 🔒 Frozen |
| **NE-014.2** | Live routing — CLI commands bypass model at zero latency | 🔒 Frozen |
| **NE-015** | Multi-step governed task execution | 🔒 Frozen |
| **NE-016** | `GovernedPlanExecutor` — kernel-supervised multi-step plans | 🔒 Frozen |
| **NE-016.1** | Plan Recovery — failed steps invalidate downstream; replanning under kernel validation | 🔒 Frozen |
| **NE-017** | Real-project OS validation on `retails` — zero fact conflation | 🔒 Frozen |
| **NE-018** | `ResearchGate` — insufficient knowledge enforces `RESEARCH_MODE` | 🔒 Frozen |
| **NE-018.1** | `KnowledgeCheckpointVerifier` — 10-domain trace-backed evidence required | 🔒 Frozen |
| **NE-018.2** | `QuestionDrivenInvestigationEngine` — question lifecycle + difficulty provenance | 🔒 Frozen |
| **NE-019** | `AutonomousProjectBootEngine` — unfamiliar workspace boot to `IMPLEMENTATION_MODE` | 🔒 Frozen |

Newer development milestones are tracked separately in the progression log and their respective pull requests.

---

## 📁 Repository Layout

```text
lisa/
├── benchmarks/          # NE benchmark harnesses + JSON/JSONL diagnostic artifacts
├── cli/                 # InputBoundaryClassifier, REPL
├── memory/              # EvidenceStore, AuthoritativeEvidenceQuery
├── runtime/             # Session, BootstrapEngine
├── tests/               # Regression and contract tests
├── tools/               # TargetInspector, Dispatcher, Filesystem capabilities
├── docs/
│   ├── FOUNDING_PHILOSOPHY.md # Model-independent intelligence and orchestration doctrine
│   └── BRAIN_ORCHESTRATION_CONTRACT.md # Proposed BOE-01 contracts and governance boundaries
├── ARCHITECTURE.md       # Immutable OS Engineering Laws (L1–L7) + Research Subsystem Contract
├── PROGRESSION_LOG.md    # Chronological experimental evidence log
├── RESEARCH.md           # Bounded empirical claims per NE milestone
└── PROJECT_MEMORY.md     # Continuation checkpoint & OS baseline
```

---

## 📜 Governance and design documents

| Document | Purpose |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Immutable kernel laws, OS diagrams, Research Subsystem Contract |
| [`docs/FOUNDING_PHILOSOPHY.md`](docs/FOUNDING_PHILOSOPHY.md) | Founding purpose, model independence, multi-brain coordination, context continuity, and design consequences |
| [`docs/BRAIN_ORCHESTRATION_CONTRACT.md`](docs/BRAIN_ORCHESTRATION_CONTRACT.md) | Proposed BOE-01 provider-neutral contracts, resource selection, task lifecycle, handoff, reconciliation, and safety rules |
| [`PROGRESSION_LOG.md`](PROGRESSION_LOG.md) | Chronological experimental evidence and milestone records |
| [`RESEARCH.md`](RESEARCH.md) | Bounded empirical claims — each claim tied to observed evidence |
| [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md) | OS version, frozen NE baseline, and continuation checkpoint |

---

## ⚡ Baseline reference

| Metric | Recorded baseline |
|---|---|
| OS Version | v2.1.0 |
| Kernel Laws | 7 (L1–L7) |
| NE Milestones Frozen | 15 (NE-009.2 → NE-019) |
| NE Baseline Test Suite | **107/107 PASS** |
| Vendor Lock-In | None by architectural design |
| Fact Conflation (NE-017 real-project validation) | `False` |

> These are historical NE baseline figures, not a claim that every newer development branch has been merged or validated by the same test count. Check the relevant pull request and CI run for current implementation evidence.
