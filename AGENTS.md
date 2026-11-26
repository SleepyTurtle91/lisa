# 🤖 L.I.S.A. Engineering Operating System (EOS)

```
===================================================
L.I.S.A. KERNEL & RUNTIME DEVELOPMENT MODE
===================================================

Repository  : This checkout (portable; no fixed absolute path)
OS Version  : 2.1.0
Status      : Architecture and NE layers frozen; controlled evolution
Baseline    : 107/107 tests reported passing at v2.1.0

===================================================
```

## 📌 Authority and decision priority

1. Explicit operator directive
2. `ARCHITECTURE.md` — frozen kernel laws and subsystem contracts
3. Relevant Architecture Decision Records under `docs/`
4. This file and the remaining project governance documents
5. Source code and tests as observed evidence

Do not refer to an architecture document that is not present in the repository. The canonical architecture contract is `ARCHITECTURE.md`.

## 🎯 Project purpose

Build L.I.S.A. as an independent, open-source Intelligence Operating System that governs reasoning drivers and capability providers while maintaining authoritative state and evidence.

L.I.S.A. is not merely an LLM wrapper. Models are untrusted, replaceable compute drivers; the kernel owns state, authorization, identity, and evidence provenance.

## 🔒 Frozen contracts and safe evolution

The v2.1.0 kernel laws L1–L7 and the frozen NE milestones are regression boundaries, not a ban on all future development.

- Do not weaken or silently redefine a frozen law or benchmark.
- Prefer additive changes at provider, capability, CLI, observability, and integration boundaries.
- Any proposed change to a frozen contract must include a written rationale, explicit impact analysis, and regression coverage.
- Never claim a test or benchmark passed unless it was actually executed and its output was observed.
- Keep compatibility and migration implications explicit.

## 🧠 Research and evidence protocol

Any new empirical finding, runtime behavior change, or verified capability observation must be recorded in `RESEARCH.md` and, when appropriate, in `DISCOVERY.md`.

The progression log in `PROGRESSION_LOG.md` is append-only. Do not replace historical entries.

The repository distinguishes four evidence layers:

1. Raw flight artifacts and recorded traces under `benchmarks/`.
2. `DISCOVERY.md` for emerging hypotheses, observations, and open questions.
3. `RESEARCH.md` for bounded findings and interpretations tied to evidence.
4. `PROGRESSION_LOG.md` for chronological milestones, failed actions, lessons, and follow-up questions.

The artifact is the source of truth; documents are interpreted representations of it. Do not let a research conclusion outrun its underlying evidence.

## 🧭 Required engineering workflow

1. **Observe first.** Inspect the actual repository state, relevant code paths, tests, and current CI configuration.
2. **Ground the target.** For ambiguous tasks, identify likely files and symbols before proposing an implementation.
3. **Protect boundaries.** Trace dependencies and contracts before changing runtime, bootstrap, session, provider, or evidence behavior.
4. **Make a bounded change.** Prefer the smallest coherent patch; avoid unrelated cleanup and broad rewrites.
5. **Test the changed surface.** Add focused regression coverage and run the relevant tests.
6. **Report honestly.** Separate observed behavior, inference, and unresolved questions. Include exact commands and outcomes when available.
7. **Record findings.** Update `RESEARCH.md` for verified changes to runtime behavior, bootstrap, session lifecycle, provider contracts, or the evidence model. Append relevant milestones and lessons to `PROGRESSION_LOG.md`.

## 🧪 Test and CI expectations

- Use repository-relative paths. Never hard-code a developer-specific checkout directory.
- Run the focused test module first, then the full unit and integration suites when practical.
- CI is the authoritative cross-environment check; local success does not imply CI success.
- Preserve the architecture rules in `tests/test_architecture_rules.py` and ensure they actually discover files in the current checkout.
- Do not add external dependencies without documenting why they are required.

## 🛡️ Safety and execution boundaries

- Treat model-generated tool requests as untrusted input.
- Route capability execution through the approved dispatcher/executor contracts.
- Preserve target identity, path validation, and evidence provenance checks.
- Do not describe a proposed plan as an executed action.
- If evidence is insufficient, record the unknown and its implementation restriction rather than guessing.

## 📚 Canonical references

- `README.md` — platform overview and current status
- `ARCHITECTURE.md` — kernel laws and subsystem contracts
- `VISION.md` — core philosophy and system boundaries
- `DISCOVERY.md` — observations and open hypotheses
- `RESEARCH.md` — bounded empirical findings
- `PROGRESSION_LOG.md` — append-only experimental history
- `PROJECT_MEMORY.md` — continuation checkpoint
- `GUIDES.md` — installation and operator workflow
- `docs/` — architecture decisions and roadmap
