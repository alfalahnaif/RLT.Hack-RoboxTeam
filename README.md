# Supplier Radar

**Evidence-based supplier discovery for public procurement.** Describe a product or service, inspect the proposed official OKPD2 category, compare historical suppliers, and open a Supplier 360 profile with source-backed company and contact information.

> **Status:** The completed intelligence integration was validated on 2 October 2026 and merged into `main` on 4 October 2026. See the [final integration report](reports/final_intelligence_integration.md) for evidence and limitations.

## What the product does

| Capability | What you get |
| --- | --- |
| Free-text supplier search | Ranked historical suppliers, evidence for each match, and clearly marked exploratory results when the category is unconfirmed. |
| OKPD2 Resolver V4 | Full official taxonomy, exact titles, Russian morphology, term specificity, historical support, and semantic supporting evidence. Results are **resolved**, **ambiguous**, or **uncertain**. |
| Optional Groq verification | `qwen/qwen3.8-27b` may select only among official candidates supplied by V4. Provider errors, invalid answers, and timeouts fall back to the deterministic resolver. Disabled by default. |
| Supplier 360 | EGRUL legal identity, OGRN/KPP, OKVED, procurement history, role evidence, and source/freshness labels in one profile. |
| Contact discovery | Verified first-party business contacts where available. Identity checks reject wrong-company websites; absent evidence stays absent. |
| Procurement analysis | Lot recommendations, market intelligence, pool health, concentration signals, and JSON/CSV export for supplier search. |

The interface supports Russian and English. For an ambiguous category, a user can review official candidates and select the intended code before treating category-specific results as confirmed.

## Validated results

| Measure | Integrated result |
| --- | ---: |
| Exact official OKPD2 titles / morphological variants | 100% / 100% on the fixed test split |
| Ambiguity detection / resolved-case precision | 93.44% / 98.46% |
| Wrong high-confidence category resolution | 0.96% |
| Contact golden set | 0 wrong-company matches; 0 invented contacts (18 suppliers) |
| Integration checks | 528 backend tests; 18 frontend tests; typecheck, lint, and production build passed |

The [integration report](reports/final_intelligence_integration.md) includes denominators, the complete A–K live acceptance matrix, Groq invocation and latency measurements, browser checks, and known limitations. The [machine-readable resolver benchmark](reports/okpd2_resolver_integrated.json) and [live acceptance output](reports/final_intelligence_acceptance.json) are committed alongside it. The sealed supplier-ranking HOLDOUT was not rerun.

## How it works

```text
Free-text query
  → full official OKPD2 taxonomy
  → exact title and Russian morphology
  → term specificity + historical support + semantic evidence
  → V4 category state and official candidates
  → optional closed-world Groq check for gated cases
  → confirmed-code ranking or labeled exploratory supplier search
  → Supplier 360 profile and source-backed contacts
```

Supplier evidence and contact provenance remain separate: a historical match does not imply a verified contact or manufacturer role.

## Technology

| Layer | Stack |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, `next-intl` |
| API and data | Python 3.11, FastAPI, Pydantic, PostgreSQL 16, pgvector, `pg_trgm`, Alembic |
| Language and retrieval | `pymorphy3` 2.0.6, Russian full-text search, IDF, pinned `intfloat/multilingual-e5-small` embeddings |
| Optional model | Groq API with `qwen/qwen3.8-27b` for candidate verification only |
| Local deployment | Docker Compose for PostgreSQL/API; Next.js dev or production server for the UI |

## Run locally

You need Docker Desktop with Compose v2 and Node.js for the frontend. For an **already populated** PostgreSQL volume and downloaded semantic model:

```bash
docker compose up -d --build
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000/ru/search`; the API is at `http://localhost:8000/api/v1`, with OpenAPI documentation at `http://localhost:8000/docs`. The frontend development environment points to this API. The API starts even if semantic embeddings are unavailable, and reports a degraded retrieval mode.

A new empty database needs the organizer CSVs in `data/raw/`, ingestion, IDF statistics, and the pinned embedding model/index before full search is available. Follow the [bootstrap and data instructions](docs/README.md) and [execution baseline](docs/HACKATHON_EXECUTION_BASELINE.md). The raw organizer files and model weights are not stored in Git.

The Groq verifier is optional. Configure `OKPD2_LLM_VERIFIER_ENABLED`, `OKPD2_LLM_MODEL`, and `OKPD2_LLM_API_KEY` in the **API container environment** to enable it; keep the key outside Git. The API remains deterministic when it is disabled or unavailable.

## API and documentation

- `POST /api/v1/supplier-search` and `GET /api/v1/supplier-search/{search_id}/export?format=json|csv`
- `GET /api/v1/suppliers/{inn}/profile` and `POST /api/v1/suppliers/{inn}/enrich`
- `GET /api/v1/recommendations/{lot_id}` and `GET /api/v1/procurements/{lot_id}/analysis`
- `GET /api/v1/market-intelligence/{okpd2}` and `GET /api/v1/health`

Project documentation starts at [`docs/README.md`](docs/README.md). The [contact discovery report](reports/p5_002a_contact_discovery.md) explains its precision checks; the [V4 report](reports/okpd2_resolver_v4.md) describes the resolver benchmark. Results reflect the documented local data and validation runs, not a guarantee of a supplier's current suitability or reachable contacts.
