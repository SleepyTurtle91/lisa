# 🤖 L.I.S.A. Engineering Operating System (EOS)

```
===================================================
L.I.S.A. KERNEL & RUNTIME DEVELOPMENT MODE
===================================================

Repository  : /home/user/development/projects/lisa
Status      : Active Development (Kernel Mode)
Phase       : Phase 1 — Core Runtime & Contracts Bootstrapping

===================================================
```

## 📌 Kernel Decision Priority

1. Explicit CTO directive
2. LISA_RUNTIME_ARCHITECTURE.md
3. AGENTS.md (this file)
4. Source code contracts

---

## 🎯 Primary Goal

Build L.I.S.A. as an independent, open-source Engineering Operating System platform that acts as the execution kernel for all client projects (`extro_pos`, `retrostash`, `music_home`, etc.).

---

## 🧠 Research & Evidence Update Protocol

Any new empirical finding, runtime behavior change, or verified capability observation must be recorded in [RESEARCH.md](RESEARCH.md) and, when appropriate, in [DISCOVERY.md](DISCOVERY.md).

The progression log in [PROGRESSION_LOG.md](PROGRESSION_LOG.md) is also a source of truth for this repository. It must be treated as an append-only record of milestones, failed actions, lessons learned, and follow-up questions.

The repository now distinguishes four layers of evidence:
1. Raw flight artifacts and recorded traces under the benchmarks directory.
2. [DISCOVERY.md](DISCOVERY.md) for emerging hypotheses, observations, and open questions.
3. [RESEARCH.md](RESEARCH.md) for disciplined, bounded findings and interpretations.
4. [PROGRESSION_LOG.md](PROGRESSION_LOG.md) for chronological milestones and operational history.

No research conclusion may outrun the underlying flight recorder evidence. The artifact is the source of truth; the documents are interpreted representations of it.

When working in this repository:
1. Observe first and gather evidence from repository state, tests, or runtime behavior.
2. If a new behavior, contract pattern, or capability is discovered, append it to [RESEARCH.md](RESEARCH.md) with the date, observed behavior, evidence, and interpretation.
3. If a milestone, failed action, regression attempt, or lesson is relevant to the research workflow, append it to [PROGRESSION_LOG.md](PROGRESSION_LOG.md) rather than replacing prior content.
4. Preserve the distinction between observed evidence and broader claims.
5. Do not leave new findings only in memory or transient conversation; the research logs are the canonical record.

If the work changes the engineering runtime, bootstrap flow, session lifecycle, provider contracts, or the evidence model, update [RESEARCH.md](RESEARCH.md) before concluding the task.

When a run yields a repeated or strengthened engineering observation, preserve the bounded wording in [RESEARCH.md](RESEARCH.md) and avoid overstating it as general autonomy.

For ambiguous engineering tasks, do not assume the user intent is already grounded. First perform repository target discovery (identify likely files, symbols, or logic paths), then select the model/scaffolding strategy based on that evidence.

Keep distinct findings separate in [RESEARCH.md](RESEARCH.md): failures involving ambiguous objectives should not be conflated with successful observations from other runtime surfaces.

When a new runtime surface is exercised, add or preserve a focused regression test and record the resulting evidence in [RESEARCH.md](RESEARCH.md) before concluding the task.

Maintain the master evidence index in [RESEARCH.md](RESEARCH.md) so the PILOT / EXP / NE chronology remains explicit and stable for future runs.

Do not replace existing entries in [PROGRESSION_LOG.md](PROGRESSION_LOG.md); append new information only.
