# 🏗️ ARCHITECTURE.md — Core Engineering Principles

```
===================================================
LISA INTELLIGENCE OPERATING SYSTEM PRINCIPLES
===================================================

Status      : FROZEN ARCHITECTURE PRINCIPLE
Version     : 2.1.0

===================================================
```

## ⚖️ The Runtime-First Principle (L.I.S.A. as an OS)

> **"L.I.S.A. is an operating environment that governs reasoning drivers and capability providers while maintaining authoritative state and evidence."**

### Operating System Full Architecture

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

### OS Control Architecture (Kernel Detail)

```text
 ┌─────────────────────────────────────────────────────────────┐
 │                         L.I.S.A. OS                         │
 │                                                             │
 │  Kernel / Governance                                        │
 │  ├─ Input Boundary (NE-014)                                 │
 │  ├─ Target Identity & Type Guarding (NE-012.1/NE-012.3)     │
 │  ├─ Context & Session Management                            │
 │  ├─ Planning & Task Orchestration (NE-015/NE-016/NE-016.1)  │
 │  ├─ Evidence & Authoritative Provenance (NE-013)             │
 │  ├─ Research Subsystem (NE-018/NE-018.1/NE-018.2/NE-019)    │
 │  ├─ FlightRecorder (Trace Ingestion)                        │
 │  └─ Activity / Operator Console (NE-010.2)                  │
 │                                                             │
 │              ┌──────────────┐                               │
 │              │ LLM DRIVER   │                               │
 │              │ INTERFACE    │                               │
 │              └──────┬───────┘                               │
 └─────────────────────┼───────────────────────────────────────┘
                       │
           ┌───────────┼────────────┐
           ▼           ▼            ▼
      ┌────────┐ ┌──────────┐ ┌──────────┐
      │ Ollama │ │  OpenAI  │ │ Gemini   │
      │ Driver │ │  Driver  │ │ Driver   │
      └────────┘ └──────────┘ └──────────┘
           │           │            │
           ▼           ▼            ▼
        qwen3        GPT-4o       Gemini
```

### Knowledge / Capability Subsystem Architecture

```text
 ┌─────────────────────────────────────────────────────────────┐
 │                    KNOWLEDGE / CAPABILITIES                 │
 │                                                             │
 │  Filesystem     Git       Flutter       Android             │
 │  Database       Shell     Browser       Network             │
 │  POS Knowledge  Docs      Codebase      Project Knowledge   │
 └─────────────────────────────────────────────────────────────┘
```

---

## 🏛️ Immutable OS Engineering Laws

1. **The LLM is an Untrusted Compute Driver**: Language models supply probabilistic reasoning as interchangeable execution backends. They are compute drivers, not the operating system authority.
2. **Kernel Supremacy**: The kernel owns target identity, resource type validation, session state, authorization, and evidence provenance. No LLM response can redefine reality or claim execution events that were not recorded by `FlightRecorder`.
3. **Knowledge is Capabilities**: Knowledge modules are capability providers exposed to the OS through deterministic tool contracts (`read_file`, `list_directory`, `exec_shell`).
4. **Deterministic Ingress Classification**: User inputs pass through `InputBoundaryClassifier` prior to model routing. Direct CLI commands and path inputs execute deterministically with zero model latency.
5. **Authoritative Evidence Boundary**: Epistemic provenance is derived strictly from `FlightRecorder` event streams (`EvidenceStore` / `AuthoritativeEvidenceQuery`), isolating `OBSERVED` tool execution from `DOCUMENTED` file text.
6. **Zero Vendor Lock-In**: Subsystems, tools, and workflows execute independently of model provider specifics.
7. **Epistemic Humility**: L.I.S.A. must not pretend to know what it has not observed. Every research question must carry an explicit kernel-tracked state. An openly-tracked unknown is valuable. A falsely-answered question is a kernel violation.

---

## 🔬 Research Subsystem Contract

Research is a first-class OS subsystem, not a freeform LLM activity.

### Investigation Entry Principle

> **"An investigation begins with questions, not assumptions."**

When L.I.S.A. opens an unfamiliar project, the correct internal state is:

> **"I don't know yet. What do I need to know? What evidence can answer it? What conflicts have I encountered? What remains unknown? Only when I have sufficient evidence may I proceed."**

### Research Loop

```text
UNKNOWN PROJECT
      ↓
RESEARCH_MODE
      ↓
ASK QUESTIONS
      ↓
INVESTIGATE
      ↓
OBSERVE EVIDENCE
      ↓
┌─────────────────────────┐
│ Discovery / Contradiction│
│ Difficulty / Failure     │
└────────────┬────────────┘
             ↓
       RECORD IT
             ↓
       INVESTIGATE MORE
             ↓
        RESOLVE IT
             ↓
      DOCUMENT FINDING
             ↓
   KNOWLEDGE CHECKPOINT
             ↓
    INTEGRITY VALIDATION
             ↓
 IMPLEMENTATION_MODE
```

### Question Lifecycle (Kernel-Enforced)

Every research question must carry one of the following kernel-tracked states:

| State | Meaning | Kernel Rule |
|---|---|---|
| `OPEN` | Under investigation, evidence not yet sufficient | **Valid** — explicitly record impact + implementation restriction |
| `INVESTIGATING` | Active evidence gathering underway | **Valid** — must not dispatch implementation tools |
| `RESOLVED` | Answered with trace-backed evidence | **Valid** — evidence source must be recorded |
| `ACCEPTED_AS_OPEN` | Legitimately unanswerable in current phase | **Valid** — impact + restriction must be documented |
| `NOT_APPLICABLE` | Question does not apply to this project | **Valid** — reason must be recorded |
| `ANSWERED` (no evidence) | Claimed resolved with no trace-backed evidence | ❌ **KERNEL VIOLATION** |

> **An `OPEN` question with a recorded implementation restriction is more valuable than a falsely `RESOLVED` question.**

Example of legitimate open knowledge:

```text
Q-017
Question:  Why does module X bypass repository Y?
Status:    OPEN
Evidence:
  - Observed X calling service Z directly.
  - No architectural documentation explains the exception.
Impact:    MEDIUM
Restriction: Do not modify the X/Y interaction boundary until resolved.
```

### Difficulty Lifecycle (Kernel-Enforced)

```text
DETECTED
   ↓
RECORDED
   ↓
INVESTIGATING
   ↓
RESOLVED / ACCEPTED-AS-OPEN
```

A difficulty may only be closed as `ACCEPTED-AS-OPEN` if:
- Its impact level is documented.
- An implementation restriction is attached to all affected modules.
- The kernel registers the open risk in the session evidence store.

---
