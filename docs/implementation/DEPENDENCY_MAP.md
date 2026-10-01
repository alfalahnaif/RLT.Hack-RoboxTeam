# Dependency Map

> ### Hackathon Day-1 amendment (2026-10-01)
> This map describes **roadmap v1 (frozen)**. Current dependencies (roadmap v2):
> `P1-001A → P1-001B → P1-001C → P1-001D → {P1-001E, P1-001F, P3-001} ; {P1-001D, P1-001E} → P1-002 → {P2-001 (optional), P2-002} → P2-003 ;`
> `P3-001 → P3-002 → P3-003 ; {P1-002, P2-003, P3-001, P3-003} → P4 → P5`. See [IMPLEMENTATION_ROADMAP Part A](../implementation/IMPLEMENTATION_ROADMAP.md).

> Derived from the real functional dependencies in [REQUIREMENTS_REVIEW §3](../analysis/REQUIREMENTS_REVIEW.md#3-feature-dependencies-functional)
> and the source execution order (P0 §89, §107). Task-level dependencies are in each task file.

## 1. Capability dependency graph

```mermaid
flowchart TD
  R[P0 Readiness<br/>rules · decisions · DS plan] --> F[P1 Foundation<br/>repo · compose · CI]
  R --> C[P1 Contracts<br/>schemas · normalization]
  F --> DB[P2 Canonical DB schema]
  C --> SEED[P1 Seed data + benchmark v0.1]
  C --> DB
  DB --> LOAD[P2 Seed loader]
  SEED --> LOAD
  LOAD --> PROJ[P2 Search projection + FTS]
  PROJ --> LEX[P2 Lexical branch]
  LEX --> AGG[P2 Aggregation]
  AGG --> API[P2 POST /search baseline]
  API --> UI0[P2 Minimal results page]
  API --> BR[P2 Benchmark runner]
  SEED --> BR
  BR --> BASE[P2 Baseline report]

  PROJ --> EMB[P3 Embeddings + vector index]
  EMB --> SEM[P3 Semantic branch]
  C --> PARSE[P3 Rule-based parser]
  PARSE --> CAT[P3 Category branch]
  LEX --> TRG[P3 Trigram]
  SEM --> UNION[P3 Union + hard filters]
  CAT --> UNION
  TRG --> UNION
  UNION --> FEAT[P3 Features]
  SEEDX[P3 Seed extension: history+evidence] --> FEAT
  FEAT --> SCORE[P3 Scorer + contributions + reason codes]
  SCORE --> HYB[P3 Hybrid /search]
  HYB --> CMP[P3 Baseline vs Hybrid]
  BASE --> CMP

  DB --> ORG[P4 Organizer adapter<br/>(dataset arrives event day)]
  C --> ORG
  ORG --> PROC[P4 Procurement records]
  ORG --> ER[P4 Entity resolution]
  PROC --> KNOWN[P4 Known/external]
  ER --> KNOWN
  PROC --> HIST[P4 Historical branch + experience]
  HIST --> UNION
  ORG --> RB[P4 Real benchmark v1.0]

  DB --> EV[P5 Evidence store]
  EV --> EXT[P5 External adapters ГИСП/ФНС]
  ER --> EXT
  EV --> CONF[P5 Confidence + flags]
  SCORE --> EXPL[P5 Templates + A vs B]
  CONF --> HYB2[P5 Evidence-backed /search]
  EXPL --> HYB2
  PARSE --> LLM[P5 Optional LLM parser]

  R --> DS[P0-005 Design System plan]
  DS --> UI[P6 Screens S-01..S-04]
  HYB2 --> PAPI[P6 Profile/meta/search-run APIs]
  PAPI --> UI

  HYB2 --> EVAL[P7 Final eval + temporal holdout]
  RB --> EVAL
  HIST --> EVAL
  UI --> HARD[P7 Hardening]
  EVAL --> DEMO[P8 Demo readiness]
  HARD --> DEMO
```

## 2. Layered build order

```text
L0  Readiness decisions ............ P0 (rules, conflicts, EDs, DS plan)        — no code
L1  Engineering foundation ......... repo · backend/frontend skeletons · compose · migrations · CI
L2  Contracts & fixtures ........... JSON Schemas · normalization · seed · benchmark v0.1 · validators
L3  Data layer ..................... canonical schema (with valid-time) · seed loader · projection
L4  Vertical slice (baseline) ...... lexical branch · aggregation · POST /search · minimal UI · benchmark runner · baseline
L5  Retrieval & ranking core ....... embeddings · semantic · trigram · parser · category · union/filters · features · scorer · reason codes
L6  Real data ...................... organizer adapter · procurement · ER · known/external · categories · historical branch · real benchmark
L7  Trust layer .................... evidence · external adapters · confidence · flags · templates · market summary · (LLM)
L8  Product experience ............. profile/meta/search-run APIs · screens · compare · feedback · E2E
L9  Proof & hardening .............. final eval · temporal holdout · latency · security · resilience · claims
L10 Demo readiness ................. clean start · offline · deploy · script · freeze
```
L6 runs **in parallel** with L5 once organizer data arrives (it depends only on L2–L3). L8 frontend work can start on the P2 API with mocked later fields once P0-005 is done.

## 3. Critical path

`P0-002 → P1-001 → P1-005 → P1-007 → P1-011 → P1-012 → P2-001 → P2-002 → P2-003 → P2-004 → P2-005 → P2-006 → P2-009 → P2-010 → P3-002 → P3-003 → P3-007 → P3-009 → P3-010 → P3-012 → P3-014 → P5-005 → P6-006 → P7-001 → P8-007`

Everything off this path is parallelizable by role (see Roadmap §4).

## 4. Hard external dependencies

| Dependency | Needed by | Fallback if missing |
|---|---|---|
| Event rules answer (OQ-01) | Start of P1 | Docs-only prep; compress P1–P3 into event day 1 |
| Organizer dataset | P4 (all) | Seed data carries the demo; metrics labeled engineering-only |
| External source access (ГИСП/ФНС) | P5-003/004 | Cached snapshots prepared in advance; one source suffices for MVP gate |
| Design System | P1-003, P6 | SCREENS.md spec; functional minimal UI for P2 |
| Embedding model weights | P3-001 | Lexical + category + trigram only (degraded mode) |
| LLM provider | P5-008 (Could) | Rule-based parser (default anyway) |
