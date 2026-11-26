# Cross-Project Intelligence (CPI)

## Purpose

Cross-Project Intelligence allows L.I.S.A. to understand and compare multiple independent software projects, discover reusable capabilities, and plan safe adaptations without conflating project-specific context.

CPI is a general L.I.S.A. capability. It must not depend on FlashPOS, ExtroPOS, a particular language, operating system, model provider, or developer workspace layout.

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
| CPI-01 | Project identity, persistent registry, CLI management, isolated project contexts | Implemented in draft PR; validation pending |
| CPI-02 | Project profile and architecture knowledge index | Planned |
| CPI-03 | Cross-project capability discovery | Planned |
| CPI-04 | Compatibility and conflict analysis | Planned |
| CPI-05 | Adaptation planning and operator approval | Planned |
| CPI-06 | Governed target execution, regression validation, and audit | Planned |

## CPI-01 operator commands

```text
lisa project add <path>
lisa project list
lisa project use <id|name>
lisa project remove <id>
lisa

# Inside the REPL
projects
project add <path>
project list
project use <id|name>
project remove <id>
```

The registry is stored at `~/.lisa/projects.json` and uses a versioned schema with atomic file replacement. Project registration persists across CLI launches. A malformed or unsupported registry fails closed rather than silently discarding registrations. The registry is separate from the recent-project list.

## CPI-01 implementation boundary

Registration resolves a canonical directory and requires at least one recognized project marker. Project IDs are deterministic for a canonical local path. A registry can retain multiple project manifests, while only one project is active at a time. Activation verifies that the project directory still exists and returns an immutable ProjectContext.

Switching projects restarts the REPL against the selected root, so a running session is not silently retargeted mid-flight. Adding a project does not read or execute its code. Registration and activation do not modify project files.

This stage deliberately does not:
- index source code, architecture, or project instructions;
- share memory or instructions between projects;
- copy, edit, or execute code across project roots;
- perform feature discovery or compatibility analysis;
- change frozen kernel/session contracts or NE laws.

Those capabilities require their own evidence, contracts, tests, and authorization design.
