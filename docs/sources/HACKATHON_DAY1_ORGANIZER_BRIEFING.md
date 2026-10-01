# Hackathon Day 1 — Official Organizer Briefing (summary)

> **Type:** Source document (rank 1 in the [source-of-truth hierarchy](../README.md#2-source-of-truth-hierarchy) — official organizer statements).
> **Event:** RLT.Hack 2026 · **Date captured:** 2026-10-01 (event day 1) · **Captured by:** team (oral briefing, summarized in English).
> **Fidelity note:** this is a faithful summary of the oral challenge clarification, not a verbatim transcript.
> Statements are recorded as the organizers made them; the team's interpretation lives in
> [HACKATHON_EXECUTION_BASELINE.md](../HACKATHON_EXECUTION_BASELINE.md). Unclear points are tracked in
> [OPEN_QUESTIONS.md](../analysis/OPEN_QUESTIONS.md#organizer-question-pack--hackathon-day-1) (OQ-33…OQ-44).
> Do not edit after capture except to append dated organizer answers at the end (§13).

---

## 1. Challenge goal

Develop and improve an **intelligent service for identifying regional suppliers, manufacturers and distributors**.

The product must have **real practical value** and fit **actual procurement / business processes**. An isolated technical
experiment is not the goal.

## 2. Business value

Expanding the supplier pool matters because:

1. More suppliers → more competition.
2. More competition → potentially lower procurement prices.
3. A larger supplier pool → less dependence on a single supplier.
4. Supplier diversification → lower risk of supply disruption.

**Supplier discovery and data enrichment are related but different problems.**

## 3. Supplier classification

The system should be able to enrich organizations with useful roles, such as:

```text
manufacturer · distributor · supplier · dealer · reseller · other intermediary
```

- **Direct manufacturers are especially valuable.**
- The role assigned to a company must be **explainable** and preferably **supported by evidence**.

## 4. Historical data

The organizers provide **real historical procurement data for 2024–2025**. It allows analysis of:
suppliers · procurement procedures · participation · winners · procurement text · product/service descriptions ·
categories · keywords · OKPD2.

## 5. First practical step

> **Download and analyze the provided CSV data.**

Consequence (stated by organizers' framing): real-dataset analysis takes priority over synthetic data generation.

## 6. OKPD2

The team must understand **what OKPD2 is, its hierarchy and its classifier levels**.

But:
- Recommendation must **not rely only on OKPD2**.
- The team must be able to explain **why a supplier was selected**, **why one supplier ranked above another**,
  **which criteria were combined**, and **which criteria had more influence**.
- The methodology must be **understandable by the whole team** (not only by its author).

## 7. Recommendation methodology

Allowed approaches include: linear scoring · weighted scoring · relevance scoring · vectorization · semantic similarity.

Warnings:
- **Avoid unnecessary complexity.** The methodology must serve the business problem.
- **Do not introduce AI merely to reproduce an answer obtainable from a simple classifier lookup.**

## 8. External supplier discovery

The system should support:
1. **Validating** existing suppliers.
2. **Identifying their roles.**
3. **Expanding the supplier pool through open sources.**

Particularly valuable use case:

```text
Low supplier diversity → detect risk → search for new suppliers → enrich the supplier pool
```

## 9. Data enrichment

External enrichment **does not need to work in real time**. It is acceptable to:
1. identify weak categories in advance,
2. find external suppliers before the presentation,
3. validate them,
4. preload the enriched data.

**Do not depend on live internet connectivity during the defense.**

## 10. User interface — stakeholders

| Stakeholder | Needs |
|---|---|
| **Procurement specialist** | Who should we invite? How many suppliers are available? How large is the supplier pool? Why is this supplier recommended? |
| **Procurement manager** | Higher-level view: supplier diversity, dependency risks, market expansion |
| **Analyst / domain expert** | Methodology, evidence, history, validation |

**Do not create three separate applications.** One integrated interface should expose information at the
appropriate level for each stakeholder.

## 11. Evaluation priorities (as stated)

| Criterion | Points | What the organizers emphasized |
|---|---:|---|
| **Functionality & solution integrity** | **30** | The system must work **end-to-end**. Disconnected excellent modules are not enough. |
| **Recommendation / matching quality** | **25** | Demonstrate **why** selected suppliers are relevant. Useful historical signals: similar procurement experience, customer experience, participation, wins, fulfillment evidence when available. |
| **Supplier pool enrichment** | *(points not stated in our notes)* | Show sources used, amount of data analyzed, newly identified suppliers, supplier roles. Even **~10 genuinely relevant newly discovered suppliers** can be meaningful. |
| **Explainability** | *(points not stated in our notes)* | Explain why a supplier was recommended **and** why a company role/status was assigned. |
| **UI** | **10** | Professional, understandable, convenient — but **do not spend most of the development time on UI**. |

> The point values for enrichment and explainability were not captured; see OQ-41.

## 12. Performance expectations

- Millisecond-level processing is **not** required.
- **~5–10 seconds per recommendation is acceptable; a one-minute wait is not.**
- The pre-defense is **≈ 5 minutes** → the product must support **several demonstration cases quickly**.

## 13. Organizer answers received after the briefing

| Date | Question (OQ) | Answer | Source |
|---|---|---|---|
| — | — | *(none yet)* | — |
