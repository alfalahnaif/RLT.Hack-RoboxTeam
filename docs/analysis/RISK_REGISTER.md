# Risk Register

> Merges P0 §73 technical risks, P0 §74 security risks, P1S §49 risks, and new risks from this analysis.
> Impact/Probability: **H / M / L**. "When" = the latest point at which mitigation must be in place.

| ID | Category | Risk | Impact | Prob. | Mitigation | When it must be addressed |
|---|---|---|:-:|:-:|---|---|
| R-01 | Operational | *(Closed 2026-10-01 — event started; moot)* **Pre-event coding may be disallowed** (A-12) → Phases P1–P3 cannot be pre-built; the whole plan compresses into 2 days | H | M | Confirm rules now (P0-002); if disallowed, prepare only docs/specs/templates allowed by rules; keep tasks small so the critical path fits the event (see Roadmap §timeboxes) | Before any code (P0) |
| R-02 | Product/Data | *(Materialized partially 2026-10-01: data is good but structurally different — no catalogs, no names; handled by ADR-H1)* Organizer dataset is poor, late, or structurally different (no text, no IDs) | H | H | Canonical adapter layer; seed data keeps pipeline working; EDA task first on event day (P4-001); semantic fallback | P1 contracts; P4-001 |
| R-03 | Data | *(Downgraded 2026-10-01: INN on every supplier row; 8 malformed)* Missing identifiers (INN/OGRN) → duplicates and weak entity resolution | H | H | Multi-stage ER L1–L4; `possible_match` without destructive merge; AMBIGUOUS_ENTITY flag | P4-004 |
| R-04 | Technical | Poor search relevance on real data | H | M | Hybrid retrieval; benchmark-driven tuning on dev split; error analysis | P3, P7-004 |
| R-05 | Data | No ground truth for real queries | H | H | Weak labels + human grading; temporal holdout; seed benchmark for engineering | P4-009 |
| R-06 | Integration / Legal | External sources (ГИСП, ФНС) unavailable, rate-limited, captcha-protected, or ToS-restricted | M | H | Pre-index & cache snapshots; allowlisted adapters; approved sources only (OQ-08); product must pass MVP gates with ≥1 source only | P0-002, P5-002 |
| R-07 | Security | LLM hallucination / prompt injection influences results | H | M | LLM only interprets query; schema-validated output; never ranking/evidence; no external text in prompts | P5-008 |
| R-08 | Operational | Internet unavailable at venue | H | M | Offline-safe mode: local DB snapshot, model baked in image, LLM off, cached evidence | P8-002 |
| R-09 | Product | *(Mitigated 2026-10-01: replay benchmark on real data, HD-06)* **Seed benchmark is self-designed** → metrics look good but prove little to the jury ("circular benchmark") | H | H | Treat seed metrics as engineering-only (A-110); build real benchmark from organizer data (P4-009); temporal holdout; claims register | P4-009, P7-007 |
| R-10 | Data | **Data leakage** in benchmark / temporal holdout (future facts visible) | H | M | ED-04 valid-time + `as_of` on all branches/features; leakage test (EC-52) | Design in P2-001; test in P7-002 |
| R-11 | Technical | Search latency above P95 targets | M | M | Candidate caps; GIN/HNSW indexes; precomputed embeddings; profiling | P3, P7-003 |
| R-12 | Technical | Embedding model slow on CPU / large corpus indexing exceeds event window | M | M | Batch, precompute, content-hash cache; limit embedded text length; subset strategy for huge corpora | P3-002, P4-008 |
| R-13 | Data | Unknown/unmapped categories | M | H | Semantic fallback; CategoryMatch N/A when intent has no category; OQ-29 | P4-006 |
| R-14 | Product | **Scope creep** (dashboards, chatbot, agents, extra sources) | H | H | MoSCoW + scope gate BR-27; freeze at P8-007; Should items only after Must gates pass | Continuous |
| R-15 | Operational | Demo failure (clean start, data, network) | H | M | Docker clean-start test; seeded snapshot; frozen demo + fallback queries; fallback laptop; health check | P8 |
| R-16 | Scalability | Dataset larger than expected | M | M | Batched ingestion/indexing; measure early in P4-001; subset for demo with documented scale path | P4-008 |
| R-17 | Data / Legal | **Personal data** of individual entrepreneurs (152-ФЗ) processed/displayed | M | M | Minimize fields; public registry data only; no contact scraping; confirm OQ-24 | P4-002 |
| R-18 | Architecture | Entity merges change IDs referenced by qrels & search runs | M | M | `SupplierRedirect`; qrels remap + benchmark version bump | P4-004 |
| R-19 | Architecture | Contract churn when organizer data arrives (schema too rigid or too loose) | H | M | Optional fields + JSONB attributes; adapters; semver contracts; decision log for changes | P1-007, P4-002 |
| R-20 | Integration (team) | Components built in isolation don't integrate (STR §13) | H | M | Vertical slice first (P2); contracts fixed before parallel work; Lead verifies end-to-end path daily | P2 |
| R-21 | UX | Design System arrives late or mismatches (RTL/Arabic vs Russian users) | M | M | Screens specified independently (SCREENS.md); P0-005 mapping; UI language decision OQ-22 | P0-005 before P6 |
| R-22 | UX | Jury cannot grasp value quickly (too technical) | H | M | Demo script UF-09; market summary first; evidence checklist; metrics slide | P8-004 |
| R-23 | Technical | Russian FTS stemming handles product specs poorly (numbers, units, Latin model names) | M | H | `simple` config for Latin/alphanumerics alongside `russian`; trigram; unit normalization in parser | P2-003, P3-004/005 |
| R-24 | Technical | LLM unavailable, slow or costly | M | M | Rule-based default; timeout + fallback; cache; optional | P5-008 |
| R-25 | Security | Public demo URL without auth abused (cost, spam feedback) | M | L | ED-15 shared credential + rate limit | P8-003 |
| R-26 | Security | Secrets committed to repository | H | L | `.env` ignored; `.env.example`; CI secret scan (Could) | P1-001 |
| R-27 | Security | Untrusted external content (HTML/JS) rendered or stored unsafely | M | M | Text-only storage, sanitization, length caps; no HTML rendering in UI | P5-002, P6 |
| R-28 | Operational | Over-tuning weights to the holdout or on the demo queries | M | M | Frozen holdout; tuning log; weights versioned | P3-014, P7 |
| R-29 | Product | Synthetic companies mistaken for real ones in demo | M | L | BR-20; demo-data notice; fictional names | P1-011, P6 |
| R-30 | Operational | Time estimates exceed event window (≈16–19 h of engineering per P0 §97 timeboxes) | H | M | Critical path first; Should/Could strictly after gates; cut list pre-agreed (Roadmap §5) | P0-007 |
| R-31 | Data | Seed data too artificial / benchmark too easy (P1S §49) | M | M | Controlled realistic Russian text; distractors; hard queries preserved | P1-011/012 |
| R-32 | Data | Random generator creates inconsistent relevance; regenerated IDs invalidate qrels (P1S §49) | H | M | Hand-crafted anchors; UUIDv5; determinism test | P1-011 |


## Hackathon Day 1 risks (2026-10-01)

| ID | Category | Risk | Impact | Prob. | Mitigation | When |
|---|---|---|:-:|:-:|---|---|
| R-33 | Data | **`is_winner` misinterpreted** (АИС ГЗ award-only vs ЭМ participants) → inflated win rates or wrong labels | H | M | HD-05 platform-separated counters; OQ-33 first; labels only from ЭМ for grade 1 | P1-001B, P1-002 |
| R-34 | Product | History/OKPD2 lookup already strong (92.5% winners seen in same class) → our ranking shows no added value | H | M | Honest baseline (P1-002); keep only features that improve dev; show explainability + pool health + expansion as value beyond ranking | P2-003 |
| R-35 | Integration | **End-to-end path not connected** (30 pts) while modules are polished | H | M | P1-002 is an end-to-end baseline before any optimization; daily golden-lot click-through | P1-002 → P4 |
| R-36 | Data/Legal | Personal data: 53% of distinct suppliers are individuals/IEs | M | H | INN + entity type only; no contacts; OQ-43 | P1-001B, P4 |
| R-37 | Operational | External enrichment curation eats team time / cannot be verified | M | M | 1–2 categories, ~10 companies, evidence template, second-person spot check; legal sources only (OQ-42) | P3-003 |
| R-38 | Technical | Ingestion of 3M items / FTS build too slow on laptop | M | M | COPY + set-based SQL; measure early; embed distinct names only | P1-001D |
| R-39 | Data | OKPD2 noise (e.g. 32.99.59.000 for hardware) and generic "тип N" item names mislead matching | M | H | Text + OKPD2 combined; OKPD2 never sole criterion; normalization of footnotes/type tokens | P1-001C, P2-003 |
| R-40 | Evaluation | Replay labels penalize relevant suppliers that simply did not bid | M | H | Report hit-rate style metrics; state limitation (BR-22); no precision claims | P1-001E, P5 |
| R-41 | Product | Concentrated-category story read as accusation against a supplier | M | L | Frame as dependency risk; no supplier names in the pool-health headline | P3-001, demo |
