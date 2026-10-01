# Phase P0 — Implementation Readiness

> ⚠️ **FROZEN (Roadmap v1, pre-hackathon).** Superseded by [Roadmap v2](HACKATHON_V2_TASKS.md) on 2026-10-01 (ADR-H1). Refer to these tasks as `v1/Pn-nnn`; do not execute them. Seed-based tasks are superseded by real organizer data (HD-01).

> Goal: close the blocking decisions for P1–P3. **No code, no dependencies installed.**
> Output of every task = updated knowledge-base files.

### P0-001 — Approve knowledge base & resolve conflicts
- **Objective:** Owner reviews the KB and decides each conflict C-00…C-19.
- **Context:** [CONFLICTS](../../analysis/CONFLICTS.md), [README §2 hierarchy](../../README.md#2-source-of-truth-hierarchy).
- **Dependencies:** —
- **Requirements:** each conflict gets status Accepted/Rejected (+ alternative chosen), date, decider; source-of-truth hierarchy approved.
- **Expected Output:** CONFLICTS.md updated; affected KB files adjusted where a recommendation was rejected.
- **Acceptance Criteria:** no conflict remains *Proposed* among C-00, C-01, C-03, C-05, C-06, C-11, C-13, C-18 (P1–P3 blockers); others may stay Proposed with a target phase.
- **Validation:** grep for `Status:** Proposed` shows only non-blocking conflicts.
- **Out of Scope:** changing product scope.

### P0-002 — Verify event rules & external-source legality
- **Objective:** Confirm what may be prepared before the event and which external sources may be used.
- **Context:** OQ-01, OQ-08, OQ-15, OQ-16, A-05, A-12, R-01, R-06, BR-38.
- **Dependencies:** —
- **Requirements:** written answer (organizer channel/rules page) on pre-event code; list of allowed sources and access method (API / downloadable dataset / scraping allowed or not) for ГИСП, ФНС/ЕГРЮЛ, EIS, company sites; submission format.
- **Expected Output:** OPEN_QUESTIONS answers; ASSUMPTIONS A-05/A-12 status updated; source allowlist table added to [DECISION_LOG](../../decisions/DECISION_LOG.md).
- **Acceptance Criteria:** OQ-01 answered or explicitly escalated; every external source in P5 has status allowed / not allowed / unknown.
- **Validation:** review by Tech Lead.
- **Out of Scope:** building any adapter.

### P0-003 — Organizer question pack & answer capture
- **Objective:** Prepare the prioritized question list for the first event hour and a place to record answers.
- **Context:** [OPEN_QUESTIONS](../../analysis/OPEN_QUESTIONS.md) (O-type), STR §15 "most important question".
- **Dependencies:** —
- **Requirements:** ≤ 12 questions ordered by blocking impact (OQ-17, OQ-02, OQ-07, OQ-03, OQ-29, OQ-05, OQ-09, OQ-12, OQ-20, OQ-21, OQ-24 + the most important question); Russian wording for each.
- **Expected Output:** "Organizer Q&A" section appended to OPEN_QUESTIONS.md.
- **Acceptance Criteria:** each question lists which task/decision its answer unblocks.
- **Validation:** Lead review.
- **Out of Scope:** answering on organizers' behalf.

### P0-004 — Accept/reject proposed engineering decisions
- **Objective:** Turn ED-01…ED-24 into binding decisions or reject them.
- **Context:** [DECISION_LOG §2](../../decisions/DECISION_LOG.md#2-proposed-engineering-decisions-this-analysis).
- **Dependencies:** P0-001.
- **Requirements:** P1–P3 blockers decided first: ED-01, 03, 04, 05, 06, 07, 09, 10, 11, 12, 13, 21, 23, 24; for rejected items, the KB files referencing them are updated.
- **Expected Output:** DECISION_LOG statuses updated.
- **Acceptance Criteria:** all P1–P3 blocking EDs are Accepted or replaced.
- **Validation:** Lead review.
- **Out of Scope:** new architecture beyond the proposals.

### P0-005 — Design System integration plan
- **Objective:** Map each screen/state in SCREENS.md to Design System patterns and decide UI locale.
- **Context:** [SCREENS](../../product/SCREENS.md), SafarFlow design system, C-19, OQ-22, A-105, A-111, A-112.
- **Dependencies:** P0-001.
- **Requirements:** decision on locale(s) and direction (RU LTR expected); per screen: page recipe, component list for each region/state; identify DS gaps (e.g. score display, contribution bar, evidence list, compare table) and whether to extend the DS library; confirm frontend stack compatibility (Next.js version, Tailwind, next-intl, `src/components/ui` layout).
- **Expected Output:** "Design System mapping" section in SCREENS.md (no visuals invented beyond DS); DS gaps list.
- **Acceptance Criteria:** every state in SCREENS.md has a mapped DS pattern or a listed gap; locale decided.
- **Validation:** Frontend + Lead review.
- **Out of Scope:** writing components or screens.

### P0-006 — Runtime environment decisions
- **Objective:** Decide LLM usage/provider, hosting target, hardware for embeddings.
- **Context:** OQ-23, OQ-31, ED-03, ED-15, ED-17, R-08, R-24.
- **Dependencies:** P0-002.
- **Requirements:** LLM: none / provider + model + key owner + cost cap; hosting: laptop / VPS / organizer; CPU/RAM available for e5 batch; internet assumptions at venue.
- **Expected Output:** entries in DECISION_LOG; ASSUMPTIONS updated.
- **Acceptance Criteria:** P5-008 and P8-003 have unambiguous targets.
- **Validation:** Lead review.
- **Out of Scope:** provisioning infrastructure.

### P0-007 — Team allocation & event timebox plan
- **Objective:** Assign tracks and timeboxes; agree cut list.
- **Context:** [Roadmap §4–5](../IMPLEMENTATION_ROADMAP.md#4-parallel-tracks-4-person-team-a-102), R-20, R-30.
- **Dependencies:** P0-004.
- **Requirements:** owner per task range; hour-by-hour plan for event days with integration checkpoints; cut list confirmed.
- **Expected Output:** "Owner" notes in the task index (e.g. `Not started (@name)`), timeline section in roadmap.
- **Acceptance Criteria:** every Must task has an owner; critical path fits the event window with ≥ 20% buffer.
- **Validation:** team walkthrough.
- **Out of Scope:** changing priorities without P0-001/P0-004.
