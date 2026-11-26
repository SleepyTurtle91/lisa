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
| CPI-05 | Review-only adaptation planning | Implemented; focused CI passing |
| CPI-06 | Explicit approval, bounded target file execution, backups, rollback, and audit | Implemented; see CPI-06.1 recovery lifecycle |

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

## CPI-06 governed execution

CPI-06 adds an explicit patch-application path. It does not copy source files automatically; an operator supplies a reviewed JSON patch and L.I.S.A. binds approval to the exact plan, source evidence hashes, target root, file paths, expected pre-change hashes, and proposed file-content hashes.

\`\`\`text
lisa project apply <source-id> <target-id> <terms> --patch <patch.json>
\`\`\`

Patch format:

\`\`\`json
{
  "changes": [
    {
      "path": "app/Inventory.kt",
      "content": "class Inventory {}\\n",
      "expected_sha256": null
    }
  ]
}
\`\`\`

For an existing file, \`expected_sha256\` is required and must match the current bytes. Use \`null\` only to create a new file. The CLI displays the exact proposed file contents and asks the operator to type the full \`APPLY <digest>\` confirmation. Any changed path, content, plan identity, source evidence, or target root changes the digest and invalidates the approval.

Execution safeguards:
- Only a \`ready_for_review\` plan with both registered projects still present is eligible.
- Only explicitly listed regular files may be created or replaced; deletes and directory creation are unsupported.
- Absolute paths, traversal, symlinks, protected paths, and writes outside the registered target root are rejected.
- Source capability evidence and target constraint files are re-hashed immediately before approval is accepted; stale plans are rejected.
- Existing files require an exact SHA-256 precondition to prevent stale-plan overwrites.
- The patch is bounded to 100 files, 1 MiB per file, and 5 MiB total.
- Backups and a JSON audit record are stored under \`~/.lisa/executions/\`, outside both project roots.
- Writes use atomic replacement. If an application or audit write fails, already-written files are rolled back.
- Approval digests are single-use; replay is rejected.
- Source project files are never modified by the executor.

CPI-06 intentionally does **not** execute shell commands, build scripts, or tests. A successful file application reports \`validation_required=true\`; the operator must run the target project's normal regression suite before accepting the adaptation. This avoids granting a cross-project adaptation implicit permission to execute arbitrary target code.

The executor is a bounded file-application capability, not a semantic code porter. Human review of the patch and target-specific regression validation remain mandatory.


## CPI-06.1 recovery and validation lifecycle

CPI-06.1 adds two explicit operator workflows:

\`\`\`text
lisa project rollback <execution-id>
lisa project validate <execution-id> --status passed|failed --command <description> --summary <result> [--evidence <relative-report-path>]
\`\`\`

### Rollback

- The operator reviews the execution ID and must type the exact \`ROLLBACK <digest>\` phrase.
- The digest binds the execution approval, target root, changed-file manifest, and backup manifest.
- The target project must still be registered at the exact original root.
- Every backup is checked against its recorded SHA-256 before any restore begins.
- Rollback proceeds only when each affected file still matches either the applied hash or the original pre-execution hash. Unrelated later edits cause a fail-closed refusal.
- Existing files are restored from verified backups, including their original permission mode; files created by the execution are removed.
- A lifecycle journal records \`rollback_in_progress\` before restoration and \`rolled_back\` after completion. An interrupted rollback can be retried safely when files are either already restored or still match the applied state.

Rollback never overwrites a target file whose current contents are neither the known applied version nor the known original version.

### Validation evidence

- The operator records a test status (\`passed\` or \`failed\`), test command/description, and concise result summary.
- An optional report file must be inside the registered target project, be a regular non-symlink file, and be no larger than 10 MiB. L.I.S.A. stores its relative path, byte count, and SHA-256; it does not copy report contents into the audit.
- The operator must type an exact \`RECORD <digest>\` phrase bound to the execution, status, command, summary, and report hash.
- L.I.S.A. checks that all adapted files still match their recorded post-execution hashes before accepting the validation record.
- Validation is labelled \`operator_reported_passed\` or \`operator_reported_failed\`. It is an operator attestation, not an independently verified result: L.I.S.A. does not execute build/test commands or claim to have observed their output.
- Validation cannot be recorded after rollback.

These lifecycle operations do not grant permission to run arbitrary target code. They provide controlled recovery and an auditable place to record human-run regression results.


## CPI-06.2 execution history and integrity inspection

CPI-06.2 adds read-only history and verification commands:

```text
lisa project history [--project <project-id>]
lisa project verify <execution-id>
```

- History lists execution IDs, source and target project names, timestamps, changed-file counts, lifecycle state, validation state, and integrity status, newest first.
- The optional project filter matches either the source or target project ID.
- Malformed execution records remain visible in history as failed-integrity entries rather than silently disappearing.
- Verification checks execution identity against its approval digest, audit schema, duplicate/path-safe manifests, changed-file/backup manifest agreement, backup SHA-256 values, current target-file state, rollback digest/restoration manifest, and validation-record digest.
- When a validation report was recorded and the target remains registered, verification rechecks the report file's size and SHA-256 against its captured metadata.
- Both commands are read-only: they do not edit execution records, project files, backups, or validation evidence.

**Integrity limitation:** these checks establish internal consistency and detect ordinary record/backup/evidence corruption. The current local JSON journal is not digitally signed, append-only, or tamper-proof. A local actor able to rewrite the audit and all related hashes can forge a coherent record. L.I.S.A. therefore reports `consistent`, not `authentic` or `tamper-proof`.
