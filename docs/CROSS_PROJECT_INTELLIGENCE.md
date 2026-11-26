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
| CPI-02 | Read-only project profiles and evidence-backed architecture inventory | Implemented; focused CI passing |
| CPI-03 | Cross-project capability discovery with evidence provenance | Implemented; focused CI passing |
| CPI-04 | Compatibility and conflict triage with architecture constraint evidence | Implemented; focused CI passing |
| CPI-05 | Review-only adaptation planning | Implemented in draft PR; validation pending |
| CPI-06 | Explicit approval, governed target execution, regression validation, and audit | Planned |

## Operator commands

```text
lisa project add <path>
lisa project list
lisa project inspect <id|name>
lisa project find <terms>
lisa project compare <source-id> <target-id> [terms]
lisa project plan <source-id> <target-id> <terms>
lisa project use <id|name>
lisa project remove <id>
lisa

# Inside the REPL
projects
project add <path>
project list
project inspect <id|name>
project find <terms>
project compare <source-id> <target-id> [terms]
project plan <source-id> <target-id> <terms>
project use <id|name>
project remove <id>
```

The registry is stored at `~/.lisa/projects.json` and uses a versioned schema with atomic file replacement. Project registration persists across CLI launches. A malformed or unsupported registry fails closed rather than silently discarding registrations. The registry is separate from the recent-project list.

## CPI-02 project profiling

Project inspection is read-only and deterministic. It inventories top-level directories and source-file paths, recognizes technology markers, and captures bounded excerpts from allowlisted project documentation and build descriptors. Each evidence item carries a relative path, evidence kind, SHA-256 digest of the original inspected bytes, inspected byte count, truncation flag, and whether secret-like values were redacted from its excerpt. Common key/password/token assignments and PEM private-key blocks are redacted before excerpts are exposed.

Source code is inventoried by filename and extension only; source contents are not ingested by CPI-02. The filesystem walk is limited to depth four and 20,000 files; the profile exposes an inventory-truncated flag when the file cap is reached. Generated output, dependency directories, VCS internals, virtual environments, and common build caches are excluded.

## CPI-03 capability discovery

Capability discovery performs deterministic lexical matching over CPI-02 project profiles. It searches documentation excerpts, top-level directory names, and source-file paths. Results include matched terms, a lexical coverage score, document evidence references with content hashes, and matching source paths.

This is candidate discovery, not semantic understanding. It does not establish that two implementations are equivalent, compatible, or safe to transplant. No source-code contents are read.

## CPI-04 compatibility triage

Compatibility triage compares two registered project profiles. It reports shared and project-specific technology markers, optionally verifies that a requested capability has source-project evidence, and extracts relevant target/source architecture or business-rule lines with their file paths and hashes.

Statuses are deliberately conservative:
- `potential_reuse`: at least one technology marker overlaps and the requested capability (if supplied) was found in source evidence;
- `adaptation_required`: no shared technology markers were detected;
- `insufficient_evidence`: technology markers are missing or a requested capability was not found.

The report does not claim there are no conflicts. Extracted constraints are review requirements, not machine-resolved rules. The tool never copies, edits, or executes code.

## CPI-05 review-only adaptation plan

`project plan <source-id> <target-id> <terms>` creates a deterministic plan preview containing source evidence references, target constraints, data/persistence review tasks, target-native adaptation guidance, regression test requirements, and an explicit operator authorization step.

A plan is either `ready_for_review` or `blocked`. It always has `authorization_required=true` and `execution_authorized=false`. Plans are not persisted and cannot execute code. The operator must review the evidence and decide whether a separate, explicitly authorized implementation request should exist.

## CPI-06 remaining boundary

CPI-06 is not implemented. No command currently copies, modifies, or executes code across project roots. Governed target execution must be designed as a separate, auditable subsystem with explicit file scope, operator approval, rollback strategy, and regression validation.
