# 📖 GUIDES.md — L.I.S.A. User Manual & Concept Guide

```
===================================================
L.I.S.A. AI ENGINEERING OPERATING SYSTEM
===================================================

Status  : STABLE (v1.1.0)
Purpose : Concept Guide, Operational Workflows & User Manual

===================================================
```

Welcome to **L.I.S.A.** (*Logical Intelligence Software Architecture*)—an **AI Engineering Operating System**.

Instead of acting as a simple chatbot or LLM wrapper, L.I.S.A. manages your entire engineering workflow by discovering projects, loading local project governance, selecting AI providers, executing deterministic tools, and enforcing performance gates.

---

## 🛠️ First-Time Setup

```bash
git clone https://github.com/SleepyTurtle91/lisa.git
cd lisa

python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode to get native 'lisa' command access
pip install -e .
```

---

## 🩺 Step 1: Verify Installation

Before working on a codebase, inspect your system environment and runtime readiness:

```bash
lisa doctor
```

**Expected Output**:
```text
🩺 L.I.S.A. Platform Diagnostics & Health Doctor (v1.1.0)
===================================================
🖥️ System Environment  : Linux (x86_64, Python 3.14.6, Git: True)
📁 Target Project Path: extro_pos (/home/user/development/projects/extro_pos)
---------------------------------------------------
🏆 Architecture Grade  : A+ (BOOT: True, AGENTS: True)
⚡ Performance Grade   : A+ (Boot Gate <15ms, Compile Gate <2ms)
---------------------------------------------------
🚀 Framework Boot Time : 6.46 ms
🛠️  Schema Compile Time: 0.01 ms
🔌 Registered Providers: 2 (Ollama: True, OpenAI: True)
🛠️  Discovered Capabilities: read_file, write_file, list_directory, flutter
💾 Historical Benchmarks: 2 run artifacts recorded in lisa/benchmarks/
===================================================
```

---

## 📁 Step 2: Preparing Your First Project

L.I.S.A. is project-aware. To unlock full 2-tier bootstrap discovery, add two governance files to your project root:

```text
my_project/
├── BOOT.md
├── AGENTS.md
└── src/
```

### Minimal `BOOT.md` Example
```markdown
# BOOT.md
Project: My App
Active Milestone: Milestone 1.0 (MVP Foundation)

Objectives:
- Build Core REST API
- Write unit tests
```

---

## 🚀 Step 3: Running L.I.S.A. Engineering Sessions

Start an engineering session on any target project directory:

```bash
lisa /path/to/my_project
```

### L.I.S.A. Lifecycle Sequence:
```text
System Boot (Inspects OS, Python, CPU, Git)
        ↓
Project Boot (Discovers BOOT.md, AGENTS.md & Capabilities)
        ↓
Kernel Initialization (State: READY)
        ↓
Provider Registration (Ollama / OpenAI)
        ↓
Tool Execution & ReAct Synthesis Loop
        ↓
Production Session Operational Report
```

---

## 💻 Command Reference

### `lisa [path]`
Runs an interactive engineering session on the target codebase.

### `lisa doctor [path]`
Runs platform health diagnostics, checks system capabilities, and asserts CI performance gates (`< 15.0 ms` boot).

### `lisa compare [path]`
Parses historical benchmark flight logs and displays generation throughput (`tok/sec`), token usage, and cache hit rate trends over time.

### `lisa benchmark [path] [model]`
Executes a flight recorder benchmark run and saves a persistent JSON benchmark artifact in `lisa/benchmarks/`.

### `lisa --help`
Displays the native command help menu.

---

## 📊 Understanding the Output Metrics

* **`Framework Boot Time` (`< 15.0 ms`)**: The time spent in L.I.S.A.'s Python kernel initialization.
* **`Provider Inference Time`**: The time spent inside the local or cloud AI provider (e.g. Ollama/Qwen). L.I.S.A. framework overhead accounts for **< 0.02%** of total turn time.
* **`Schema Cache Hit Rate (%)`**: The percentage of compiled function-calling tool schemas reused from memory.
* **`Throughput Rate (tok/sec)`**: Model token generation throughput speed.

---

## 🔄 Recommended Daily Workflow

1. **Morning**: Verify platform health with `lisa doctor`.
2. **Development**: Run `lisa /path/to/project` to inspect code and execute tasks.
3. **Benchmarking**: Measure model throughput changes using `lisa benchmark`.
4. **Trend Analysis**: Inspect performance history with `lisa compare`.

---

## 📚 Core Documentation Links

* [**README.md**](file:///home/user/development/projects/lisa/README.md) — Platform overview
* [**ARCHITECTURE.md**](file:///home/user/development/projects/lisa/ARCHITECTURE.md) — Kernel & Subsystem design
* [**DECISIONS.md**](file:///home/user/development/projects/lisa/docs/DECISIONS.md) — Architecture Decision Records (ADRs #001 – #013)
* [**ROADMAP.md**](file:///home/user/development/projects/lisa/docs/ROADMAP.md) — Execution roadmap
