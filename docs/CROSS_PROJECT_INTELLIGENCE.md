# Cross-Project Intelligence (CPI)

## Purpose

Cross-Project Intelligence allows L.I.S.A. to understand and compare multiple independent software projects, discover reusable capabilities, and plan safe adaptations without conflating project-specific context.

CPI is a general L.I.S.A. capability. It must not depend on a particular project, programming language, operating system, model provider, or developer workspace layout.

## Non-negotiable boundaries

1. **Identity before knowledge:** every project is resolved to a canonical root and deterministic local identity before it can enter the registry.
2. **Isolation by default:** each operation receives an immutable context identifying exactly one project. Project-specific instructions, architecture, data models, and evidence are never implicitly shared.
3. **Read before reuse:** a source capability must be inspected and evidenced before compatibility is assessed.
4. **Adapt, do not transplant:** a capability is adapted to the target project's architecture and conventions; blind file copying is not a CPI operation.
5. **Explicit target authorization:** CPI may inspect registered projects, but changes to a target project require explicit operator authorization.
6. **Traceability:** future CPI operations must record source identity, target identity, evidence, compatibility decisions, and validation results.
7. **Portability:** project identity and discovery must not rely on one operating system's path layout.

## Delivery sequence

| Stage | Capability | Status |
|---|---|---|
| CPI-01 | Project identity, persistent registry, CLI management, isolated project contexts | Implemented; focused CI passing |
| CPI-02 | Read-only project profiles and evidence-backed architecture inventory | Implemented in draft PR; validation pending |
| CPI-03 | Cross-project capability discovery | Planned |
| CPI-04 | Compatibility and conflict analysis | Planned |
| CPI-05 | Adaptation planning and operator approval | Planned |
| CPI-06 | Governed target execution, regression validation, and audit | Planned |

## CPI-01 operator commands

```text
lisa project add <path>
lisa project list
lisa project inspect <id|name>
lisa project use <id|name>
lisa project remove <id>
lisa

# Inside the REPL
projects
project add <path>
project list
project inspect <id|name>
project use <id|name>
project remove <id>
```

The registry is stored at `~/.lisa/projects.json` and uses a versioned schema with atomic file replacement. Project registration persists across CLI launches. A malformed or unsupported registry fails closed rather than silently discarding registrations. The registry is separate from the recent-project list.

## CPI-02 project profiling

Project inspection is read-only and deterministic. It inventories top-level directories and source-file paths, recognizes technology markers, and captures bounded excerpts from allowlisted project documentation and build descriptors. Each evidence item carries a relative path, evidence kind, SHA-256 digest of the inspected bytes, inspected byte count, and truncation flag.

Source code is inventoried by filename and extension only; source contents are not ingested by CPI-02. Generated output, dependency directories, VCS internals, virtual environments, and common build caches are excluded. Evidence is generated on demand and is not yet persisted as a long-lived knowledge index.

## CPI-02 operator behavior

`project inspect <id|name>` prints the project profile, detected technologies, top-level directories, source-file count, and evidence references. It does not print document excerpts or change project files.

## Remaining boundary

CPI-02 does not yet:
- share project instructions, memories, or source code between projects;
- discover reusable features or business capabilities;
- determine architectural compatibility;
- copy, edit, or execute code across project roots;
- change frozen kernel/session contracts or NE laws.

Those capabilities require their own evidence, contracts, tests, and authorization design.
