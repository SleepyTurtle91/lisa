# 🧠 L.I.S.A. — Intelligence Operating System (v2.1.0)

```
===================================================
L.I.S.A. INTELLIGENCE OPERATING SYSTEM
===================================================

Version     : v2.1.0
Status      : FROZEN — ALL NE LAYERS LOCKED 🔒
Last Audit  : 2026-08-13
Test Suite  : 107/107 PASS (100%)

===================================================
```

---

## 🏛️ What is L.I.S.A.?

**L.I.S.A.** is an **Intelligence Operating System** — not an AI assistant.

> *"L.I.S.A. is an operating environment that governs reasoning drivers and capability providers while maintaining authoritative state and evidence."*

L.I.S.A. sits between the **operator** and the **LLM**, enforcing kernel laws that no reasoning provider can override.

```text
                     👤 OPERATOR
                          │
                          ▼
          ┌───────────────────────────────┐
          │           L.I.S.A. OS         │
          │                               │
          │  Kernel / Governance          │
          │  Research Subsystem           │
          │  Planning Subsystem           │
          │  Evidence Subsystem           │
          │  Execution Subsystem          │
          └───────────────┬───────────────┘
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
    🤖 LLM DRIVERS                 🧰 KNOWLEDGE
    reasoning/compute              capabilities
           │                             │
           └──────────────┬──────────────┘
                          ▼
                    REAL WORLD
                          │
                          ▼
               📼 FLIGHT RECORDER
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
    AUTHORITATIVE                    OPERATOR
       EVIDENCE                        VIEW
```

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

### Research Loop

```text
UNKNOWN PROJECT → RESEARCH_MODE → ASK QUESTIONS → INVESTIGATE
      → OBSERVE EVIDENCE → RECORD DISCOVERIES / CONTRADICTIONS
      → INVESTIGATE MORE → RESOLVE → DOCUMENT FINDING
      → KNOWLEDGE CHECKPOINT → INTEGRITY VALIDATION
      → IMPLEMENTATION_MODE
```

### Question Lifecycle (Kernel-Enforced)

| State | Kernel Rule |
|---|---|
| `OPEN` | Valid — record impact + implementation restriction |
| `INVESTIGATING` | Valid — implementation tools blocked |
| `RESOLVED` | Valid — evidence source must be recorded |
| `ACCEPTED_AS_OPEN` | Valid — impact + restriction must be documented |
| `NOT_APPLICABLE` | Valid — reason must be recorded |
| `ANSWERED` (no evidence) | ❌ **Kernel violation** |

---

## 🧪 NE Benchmark Suite (107/107 PASS)

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

---

## 📁 Repository Layout

```
lisa/
├── benchmarks/          # NE benchmark harnesses + JSON/JSONL diagnostic artifacts
├── cli/                 # InputBoundaryClassifier, REPL
├── memory/              # EvidenceStore, AuthoritativeEvidenceQuery
├── runtime/             # Session, BootstrapEngine
├── tests/               # 107-test regression suite
├── tools/               # TargetInspector, Dispatcher, Filesystem capabilities
├── ARCHITECTURE.md      # Immutable OS Engineering Laws (L1–L7) + Research Subsystem Contract
├── PROGRESSION_LOG.md   # Chronological experimental evidence log
├── RESEARCH.md          # Bounded empirical claims per NE milestone
└── PROJECT_MEMORY.md    # Continuation checkpoint & OS version
```

---

## 📜 Governance Documents

| Document | Purpose |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Immutable kernel laws, OS diagrams, Research Subsystem Contract |
| [`PROGRESSION_LOG.md`](PROGRESSION_LOG.md) | Chronological evidence log for all NE milestones |
| [`RESEARCH.md`](RESEARCH.md) | Bounded empirical claims — each claim tied to observed evidence |
| [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md) | OS version, freeze checkpoint, continuation state |

---

## ⚡ Quick Stats

| Metric | Value |
|---|---|
| OS Version | v2.1.0 |
| Kernel Laws | 7 (L1–L7) |
| NE Milestones Frozen | 15 (NE-009.2 → NE-019) |
| Test Suite | **107/107 PASS (100%)** |
| Vendor Lock-In | None |
| Fact Conflation (NE-017 real-project validation) | `False` |

