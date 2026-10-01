# Golden demo cases v1.0.0 (P1-001F)

> **Golden cases are for qualitative demonstration and debugging only** — live demo, screenshots, explanation examples, final
> presentation. They are **not** the benchmark: quantitative quality is measured only on [`../replay/`](../replay/).
> Prohibited: benchmark tuning, holdout replacement, reporting quantitative quality, claiming a #1 supplier before P1-002 evaluates it.

`golden_cases.json` = case cards whose facts are generated from PostgreSQL (`python -m app.cli benchmark golden`; re-check with
`benchmark golden-validate`). History facts use only `publish_date < target date`. No supplier INNs/names are stored.

| Role | Lot | Date | Subject → item | OKPD2 | Observed suppliers | Demo capability |
|---|---|---|---|---|---:|---|
| **Primary** | 5718896 | 2025-06-16 | «Поставка компьютерного оборудования» → Ноутбук Acer Aspire 5 A515-57-50R7 15.6" | 26.20.11.110 | 13 | generic title, specific item; model identifier |
| **Primary** | 5545252 | 2025-02-04 | Office chairs for a school → «Кресло офисное Бюрократ CH-695NLT» + full spec | 31.01.11.150 | 14 | spec-rich text; non-trivial ranking (winner mid-pack by award counts) |
| **Primary** | 5542696 | 2025-02-03 | Nitrile examination gloves | 22.19.60.119 | 15 | honest hard case: winner had one prior same-code award |
| Backup | 6022687 | 2025-12-17 | «Поставка компьютерной техники в 2025 году» → HP LaserJet Pro 4103dw MFP + ASUS VivoBook 17X | 26.20.11.110, 26.20.18.120 | 13 | multi-item, multi-OKPD2, identifiers |
| Backup | 5612123 | 2025-03-25 | «Поставка интерактивной панели» (item = title) | 26.20.13.000 | 10 | OKPD2/category evidence when text adds nothing (original UC-01 example) |

## Demo stories (primary) — no results are claimed

1. **5718896** — INPUT: «Поставка компьютерного оборудования» → EVIDENCE: ТРУ names a specific Acer laptop model (OKPD2 26.20.11.110) →
   SHOULD DEMONSTRATE: retrieval and explanation from item-level evidence, not the generic lot subject.
2. **5545252** — INPUT: office chairs for a St Petersburg school → EVIDENCE: brand/model + seat dimensions, load, warranty in the ТРУ line →
   SHOULD DEMONSTRATE: relevance explained by item text + OKPD2 + history; simple award counts alone are not enough.
3. **5542696** — INPUT: nitrile examination gloves → EVIDENCE: precise ТРУ line (non-powdered, non-sterile, nitrile) →
   SHOULD DEMONSTRATE: transparent evidence for each candidate, including when the eventual winner has thin history.

## Descriptive difficulty (historical award counts, same definition as P1-001A §9 — not a system result)

| Lot | Prior same-code winning suppliers | Winner's prior same-code awards | Winner's award-count rank (tie span) |
|---|---:|---:|---|
| 5718896 | 294 | 72 | 2 |
| 5545252 | 463 | 6 | 70–83 |
| 5542696 | 290 | 1 | 155–290 |
| 6022687 | 519 | 20 | 27–29 |
| 5612123 | 178 | 12 | 9–10 |

All five winners were seen before (any role) in the same OKPD2 code — the difficulty is ranking among hundreds of candidates.

**Not selected:** 5659204 (duplicates the laptop story), 5875992 (mixed mouse + TV — harder to narrate), 5548828 (weak single-mouse story),
5510873 (already a replay-benchmark query). **Benchmark overlap: none** (checked against `benchmark/replay/queries.csv`; 6022687 is not a
benchmark query — future benchmark versions should also exclude it explicitly). The concentrated-category demo (pool health,
e.g. OKPD2 10.51.11.141) is category-level and is chosen in P3-001, not here.
