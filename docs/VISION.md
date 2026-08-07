# 👁️ VISION.md — L.I.S.A. Product & Platform Vision

```
===================================================
L.I.S.A. ENGINEERING OPERATING SYSTEM
===================================================

Status      : APPROVED PLATFORM VISION CONSTITUTION
Version     : 1.0.0
Tag         : v1.0.0-alpha ("The Foundation Release")

===================================================
```

---

## 🎯 1. What Problem Does L.I.S.A. Solve?

Most AI coding assistants and frameworks are built as **application wrappers around specific LLM providers**. This results in:
* Vendor lock-in and fragile prompt-dependent hacks.
* Lack of deterministic runtime control and unhandled AI execution failures.
* Non-reusable tooling across different developer projects.

**L.I.S.A. (Logical Intelligence Software Architecture)** solves this by separating **deterministic runtime control** from **probabilistic AI intelligence**. Language models act as interchangeable execution backends; the L.I.S.A. kernel owns session state, tool resolution, contract enforcement, and failure recovery.

---

## 👤 2. Who Is It For?

* **Software Engineers & CTOs**: Who require reproducible, predictable, testable AI engineering workflows.
* **Multi-Project Developers**: Who need a single, consistent engineering kernel across diverse domain codebases (`ExtroPOS`, `Music Home`, `RetroStash`, `Kakeibo`).
* **Platform Engineers**: Who want a contract-driven platform that supports local models (Ollama, LM Studio) and cloud APIs (OpenAI, Claude, Gemini) interchangeably.

---

## 🚫 3. What Is Deliberately Out of Scope?

* **Proprietary LLM Hosting**: L.I.S.A. is an execution kernel, not a model hosting provider.
* **Ad-hoc Custom Scripting**: L.I.S.A. does not execute unvalidated or non-contract-compliant custom code paths.
* **Generic Chatbot UI**: L.I.S.A. is built as a deterministic engineering operating system, not a conversational novelty interface.

---

## 🔒 4. Immutable Principles (Never Change)

1. **Runtime Supremacy**: The deterministic runtime kernel owns all system decisions. Language models only provide probabilistic reasoning.
2. **Provider Neutrality**: No LLM backend receives special treatment. All providers execute through `ProviderManifest`, `ProviderSelector`, and `InferenceEngine`.
3. **The Contract Runtime Pattern**: All subsystems MUST adhere strictly to the 9-part pattern (`Manifest`, `Context`, `Request`, `Result`, `Registry`, `Resolver`, `Executor`, `State`, `Tests`).
4. **Automated Architectural Enforcement**: Boundary laws and dataclass purity MUST be enforced by automated CI tests (`test_architecture_rules.py`), not manual trust.
