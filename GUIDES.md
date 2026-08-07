# 📖 GUIDES.md — L.I.S.A. Quickstart & Command Reference

```
===================================================
L.I.S.A. AI Engineering Operating System
===================================================

Status  : STABLE (v1.1.0)
Purpose : User Onboarding, Command Guide & CLI Reference

===================================================
```

Welcome to **L.I.S.A.** (Local Engineering Assistant)—an AI Engineering Operating System designed to run deterministic, tool-calling engineering agents on your local codebase.

---

## 🚀 Quickstart Guide (30 Seconds)

### 1. Prerequisites
Ensure you have the following installed on your machine:
* **Python**: 3.10 or higher
* **Git**: System git installed
* **Ollama**: Local AI runner with `qwen3:1.7b` or `qwen3:4b` pulled (`ollama pull qwen3:1.7b`)

### 2. Set Python Path
Set `PYTHONPATH` to point to your development directory:

```bash
export PYTHONPATH=/path/to/development/projects
```

---

## 💻 CLI Commands & Usage

L.I.S.A. provides three primary operational entry points:

### 1. Interactive Session (Default)
Run an AI session against a target project workspace:

```bash
python3 cli/main.py /path/to/target_project
```

**Example Output**:
```text
🤖 L.I.S.A. Engineering Operating System (v1.1.0)
===================================================
💻 System Environment : Linux (x86_64, Python 3.14.6)
🔍 Discovered Project  : extro_pos (/home/user/development/projects/extro_pos)
   ✓ BOOT.md present  : True
   ✓ AGENTS.md present: True
   ✓ Capabilities     : read_file, write_file, list_directory, flutter

⚡ Initializing L.I.S.A. Kernel...
   ✓ State: READY

🚀 Executing Sample Prompt...
📥 Assistant Response: The active milestone is Milestone 2.0 — Experience Foundation v2.0.

📊 Session Operational Report
---------------------------------------------------
   ✓ Target Project   : extro_pos
   ✓ Reasoning Turns : 2
   ✓ Tool Calls Made : 1
   ✓ Total Tokens     : 1479
   ✓ Total Latency   : 26628.34 ms
   ✓ Execution Status: SUCCESS
---------------------------------------------------
```

---

### 2. Platform Diagnostics (`doctor`)
Run health checks, architecture grading, and verify CI performance gates:

```bash
python3 cli/main.py doctor /path/to/target_project
```

**Example Output**:
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

### 3. Historical Benchmark Comparison (`compare`)
Analyze token throughput and latency trends across historical runs:

```bash
python3 cli/main.py compare
```

**Example Output**:
```text
📊 L.I.S.A. Historical Benchmark Trend Analysis
=========================================================================================================
Timestamp            | Model           | Overhead (ms)   | Inference (ms)  | Tokens     | Tok/Sec    | Cache Hit %
---------------------------------------------------------------------------------------------------------
2026-08-08 03:24     | qwen3:1.7b      | 3.52            | 42367.91        | 1959       | 24.07      | 50.0      
2026-08-08 03:24     | qwen3:1.7b      | 3.5             | 8980.16         | 549        | 30.07      | 0.0       
=========================================================================================================
```

---

### 4. Flight Recorder Benchmark (`benchmark.py`)
Execute a benchmark flight recorder run and record a persistent JSON artifact:

```bash
python3 cli/benchmark.py /path/to/target_project qwen3:1.7b
```

---

## 🛠️ Tool Calling & Capabilities

L.I.S.A. exposes deterministic filesystem tools to local models via native function calling:

| Tool | Capability | Description |
| :--- | :--- | :--- |
| `read_file` | `FILESYSTEM_READ` | Reads complete contents of a target workspace file |
| `write_file` | `FILESYSTEM_WRITE` | Writes code contents to a target workspace file |
| `list_directory` | `FILESYSTEM_LIST` | Lists directory files and subdirectories |

---

## 🧪 Running Automated Unit & Performance Gate Tests

Run the complete test suite (34 automated tests, including layer boundary rules and CI performance gates):

```bash
PYTHONPATH=/path/to/development/projects python3 -m unittest discover -s tests
```

---

## ❓ FAQ & Troubleshooting

* **Q: Why does the first prompt take ~20 seconds?**
  * *A*: L.I.S.A.'s internal framework overhead is under **4.3 ms**. The remaining latency is spent inside your local GPU/CPU evaluating LLM function call schemas.
* **Q: How does L.I.S.A. protect itself from getting slower?**
  * *A*: `tests/test_performance_gate.py` fails CI automatically if framework boot exceeds **15.0 ms** or schema compilation exceeds **2.0 ms**.
