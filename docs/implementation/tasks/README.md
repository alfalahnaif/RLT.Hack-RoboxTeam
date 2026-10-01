# Implementation Tasks

> **Current task list: [HACKATHON_V2_TASKS.md](HACKATHON_V2_TASKS.md) (Roadmap v2, authoritative from 2026-10-01 — ADR-H1).**
> The per-phase files below are **Roadmap v1 (frozen, historical)**; refer to their tasks as `v1/Pn-nnn`. Many v2 tasks say "reuse v1/…" for detail.

Status is tracked **only** in the [task index](../IMPLEMENTATION_ROADMAP.md#task-index).

| File | Phase |
|---|---|
| **[HACKATHON_V2_TASKS.md](HACKATHON_V2_TASKS.md)** | **Roadmap v2 — P1-001A…F, P1-002, P2-001…003, P3-001…003, P4, P5 (current)** |
| [P0_readiness.md](P0_readiness.md) | P0 — Implementation Readiness (decisions only, no code) |
| [P1_foundation_contracts.md](P1_foundation_contracts.md) | P1 — Engineering Foundation & Contracts |
| [P2_baseline_vertical_slice.md](P2_baseline_vertical_slice.md) | P2 — Keyword Baseline Vertical Slice |
| [P3_hybrid_ranking.md](P3_hybrid_ranking.md) | P3 — Hybrid Retrieval & Ranking |
| [P4_organizer_data.md](P4_organizer_data.md) | P4 — Organizer Data & Entity Resolution |
| [P5_evidence_confidence.md](P5_evidence_confidence.md) | P5 — Evidence, Confidence & Market Expansion |
| [P6_product_experience.md](P6_product_experience.md) | P6 — Product Experience (requires Design System) |
| [P7_evaluation_hardening.md](P7_evaluation_hardening.md) | P7 — Evaluation & Hardening |
| [P8_demo_readiness.md](P8_demo_readiness.md) | P8 — Demo & Release Readiness |

## Task template

```text
### Pn-nnn — Title
Objective:         one sentence
Context:           links to KB sections / BR / NFR / EC / ED / OQ
Dependencies:      task IDs (+ external)
Requirements:      bullet list — what must be true
Expected Output:   files / endpoints / reports
Acceptance Criteria: verifiable statements
Validation:        commands / tests that prove it
Out of Scope:      explicit exclusions
```

## Execution rules
1. Execute only after explicit owner go-ahead; one task at a time unless told otherwise.
2. All dependencies must be `Done` (or explicitly waived by the owner).
3. Read every linked context item before starting. If a requirement conflicts with a higher source, stop and log a conflict.
4. Stay inside *Out of Scope*; new ideas → OPEN_QUESTIONS or a new task, not silent scope growth (BR-27).
5. Finish against the [Definition of Done](../DEFINITION_OF_DONE.md) and update the index.
