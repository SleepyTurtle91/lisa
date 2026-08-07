# 🏗️ L.I.S.A. Runtime Architecture Specification (v3.0.0)

```
===================================================
L.I.S.A. ENGINEERING OPERATING SYSTEM
===================================================

Status      : APPROVED ARCHITECTURE SPECIFICATION
Version     : 3.0.0
Mode        : Autonomous Standalone Engineering Operating System
Backend     : Multi-Provider (Ollama Native, OpenAI, Gemini, Claude, LM Studio)

===================================================
```

---

## 1. Runtime Lifecycle

The runtime execution flow separates **deterministic setup** from **probabilistic AI reasoning**:

```text
               lisa start
                   │
  ┌────────────────┴────────────────┐
  │ DETERMINISTIC BOOTSTRAP ENGINE  │
  ├─────────────────────────────────┤
  │ 1. Project Discovery            │
  │ 2. Read BOOT.md & AGENTS.md     │
  │ 3. Memory & Session Init        │
  │ 4. Plugin Auto-Registration     │
  │ 5. Tool Schema Compilation      │
  └────────────────┬────────────────┘
                   │
  ┌────────────────┴────────────────┐
  │ PROBABILISTIC AI ENGINE         │
  ├─────────────────────────────────┤
  │ 1. Dispatch Prepared Prompt     │
  │ 2. Tool Invocation Loop         │
  │ 3. Engineering Execution        │
  │ 4. Verification & Checkpoint    │
  └─────────────────────────────────┘
```

---

## 2. Component Boundaries & Runtime Subsystems

```text
                         L.I.S.A. Runtime
                                 │
   ┌───────────────┬─────────────┼───────────────┬───────────────┐
   │               │             │               │               │
BootstrapEngine  ToolManager ProviderManager MemoryManager  PluginManager
   │               │             │               │               │
 BOOT.md        File/Bash/    Ollama/GPT/      Session/        Android/
 AGENTS.md      Git/SQLite    Claude/Gemini    Context         Compose/POS
```

* **Bootstrap Engine**: Loads engineering constitution, target sprint parameters, and environment state.
* **ProviderManager**: Manages abstraction adapters to local models (Ollama/LM Studio) and cloud APIs (OpenAI, Gemini, Claude).
* **ToolManager**: Registers, validates schemas, and dispatches native tool executions (file reads/writes, bash, git, sqlite, etc.).
* **MemoryManager**: Handles context budgeting, conversation state, long-term operational history, and token compression.
* **PluginManager**: Mounts domain-specific extensions (e.g. `extropos`, `android`, `flutter`, `docker`).

---

## 3. Core Interface Specifications

### 3.1 Provider API Boundary

```kotlin
interface Provider {
    val id: String
    val name: String
    
    suspend fun chat(request: ChatRequest): ChatResponse
    suspend fun stream(request: ChatRequest): Flow<ChatChunk>
    suspend fun embeddings(text: String): List<Float>
    suspend fun isHealthy(): Boolean
}
```

### 3.2 Tool API Boundary

```kotlin
interface Tool {
    val name: String
    val description: String
    val parametersSchema: JsonObject
    
    suspend fun execute(arguments: JsonObject): ToolResult
}

interface ToolManager {
    fun registerTool(tool: Tool)
    fun getCompiledSchemas(providerId: String): JsonArray
    suspend fun dispatch(call: ToolCall): ToolResult
}
```

### 3.3 Plugin SDK Boundary

```kotlin
interface LisaPlugin {
    val id: String
    val name: String
    val version: String
    
    fun registerTools(): List<Tool>
    fun registerPrompts(): List<PromptTemplate>
    fun registerKnowledge(): List<KnowledgeBase>
}
```

---

## 4. Stability Guarantees & Non-Negotiable Laws

1. **Zero OpenClaw Lock-In**: OpenClaw is strictly reduced to an optional legacy adapter; core runtime functions independently.
2. **Deterministic-First Boot**: Boot sequencing, prompt/rule context loading, and tool registration execute in 100% deterministic code before any model invocation.
3. **Multi-Backend Provider Neutrality**: Standardized JSON tool schema mapping ensures identical tool behavior across Ollama (`qwen3:4b`, `llama3.2`), OpenAI, Claude, or Gemini backends.
4. **Context Budget Enforcement**: MemoryManager strictly manages token windows and fast-boots within specified file budgets.

---

## 5. Architectural Phase Roadmap

| Phase | Subsystem Target | Objective |
| :--- | :--- | :--- |
| **Phase 1** | Core Runtime Directory Structure | Establish `lisa/core`, `providers`, `tools`, `memory`, `plugins`, `bootstrap` |
| **Phase 2** | ProviderManager Adapters | Implement `OllamaProvider` (Native JSON schema function calling) and multi-cloud providers |
| **Phase 3** | ToolManager Registry | Standardize `read_file`, `write_file`, `bash`, `git`, `sqlite` tool schemas and dispatch logic |
| **Phase 4** | Bootstrap Engine | Wire `lisa start` sequence: project discovery → `BOOT.md` → `AGENTS.md` → context assembly |
| **Phase 5** | Domain Plugin Engine | Implement `LisaPlugin` loader for extensible POS, Android, and Flutter tooling |
