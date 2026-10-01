# User Roles & Permissions

> ### Hackathon Day-1 amendment (2026-10-01)
> Organizer stakeholders map to **levels of detail in one interface**, not to permissions or separate apps (briefing §10):
> procurement specialist → shortlist & reasons · procurement manager → pool health, diversity, dependency, expansion · analyst/domain expert →
> methodology, evidence, history, validation. MVP access model (no auth, D-12) is unchanged.

> Sources: Phase 0 §2.2–2.3, D-12 ("No auth for hackathon demo"), §15 (full RBAC out of scope), §62 (debug endpoint), §102 (pilot RBAC).

## 1. MVP position

The MVP has **no authentication and a single effective role** (D-12). Personas differ in *goals*,
not in *permissions*. This is an accepted decision — but it has consequences listed in §4.

## 2. Actors

| Actor | Kind | MVP access |
|---|---|---|
| **Anonymous user** (any persona: specialist, analyst, manager, jury) | Human, via UI | All read features: search, filter, profile, evidence, compare; submit feedback (Should) |
| **Operator** (team member) | Human, via CLI / shell | Ingestion (`ingest …`), index rebuild, embedding build, benchmark runs, seed generation. Not exposed over HTTP. |
| **Developer (debug)** | Human, via API | `/api/v1/debug/*` — only when `DEBUG=true` (Phase 0 §62) |
| **External source** | System | No inbound access. Supplier Radar pulls from it through controlled adapters. Its content is untrusted (NFR-SEC-01). |
| **LLM provider** (optional) | System | Receives the query text only; returns an interpretation. Cannot call tools or influence ranking (BR-09, BR-24). |

## 3. Permission matrix (MVP)

| Capability | Anonymous (UI/API) | Operator (CLI) | Debug (DEBUG=true) |
|---|:---:|:---:|:---:|
| `POST /search` | ✅ | — | ✅ |
| `GET /suppliers/{id}`, `/evidence` | ✅ | — | ✅ |
| `GET /meta/filters`, `GET /health` | ✅ | — | ✅ |
| `POST /feedback` | ✅ (Should) | — | ✅ |
| `POST /debug/rank` and other debug routes | ❌ (route absent) | — | ✅ |
| Ingest data / rebuild index / build embeddings | ❌ | ✅ | ❌ |
| Run benchmark | ❌ | ✅ | ❌ |
| Modify ranking weights | ❌ (config file, versioned) | ✅ via config + commit | ❌ |
| Modify supplier data manually | ❌ | ❌ — use adapters/seed (demo must run without manual DB edits) | ❌ |

## 4. Consequences & missing rules (see [REQUIREMENTS_REVIEW](../analysis/REQUIREMENTS_REVIEW.md) G-15)

1. **Public deployment without auth** exposes the API (and any paid LLM calls) to anyone with the URL.
   **[ER] ED-15:** if the demo is deployed on a public host, protect it with a single shared credential at
   the reverse proxy + basic per-IP rate limiting on `/search`. This does not violate D-12 (no user model).
2. **Feedback without identity** cannot be attributed or de-duplicated. Accept for MVP; store
   `request_id` + `supplier_id` + timestamp only. Treat as weak signal.
3. **Personal data:** individual entrepreneurs (12-digit INN) are natural persons. Displaying/storing
   their data is subject to Russian personal-data law (152-ФЗ). See R-17, OQ-24.
4. **Debug routes** must not be registered at all when `DEBUG=false` (not merely hidden).

## 5. Pilot-stage roles (future — do not build)

| Role | Intended permissions |
|---|---|
| Procurement Specialist | Search, profile, compare, feedback, export, saved searches |
| Category Analyst | + market/category analytics |
| Procurement Manager | + sourcing-quality and supplier-pool dashboards |
| Data Administrator | Source management, refresh scheduling, ingestion monitoring, data quality |
| Org Admin | User & organization management (with SSO/RBAC at SaaS stage) |

Design implication for MVP code: keep an `actor`/`request context` object in the request pipeline
(currently anonymous) so auth can be added later without touching domain services.
