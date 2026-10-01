# P3-002A — External Candidate Reconciliation

Target exact observed OKPD2 value: `10.51.11.141`. History cutoff: `publish_date < 2026-01-01`.
Supplied names are unverified inputs; INN validity and historical reconciliation are separate from evidence verification.

## Results

| INN | Supplied name | INN valid | Global history | Exact category | First / last observed | Historical lots / wins | Exact lots / wins | Status | Verification |
|---|---|---|---|---|---|---:|---:|---|---|
| `7622012124` | ООО «Переславский молочный комбинат» | True | False | False | — / — | 0 / 0 | 0 / 0 | EXTERNAL_NEW | UNVERIFIED |
| `0257011170` | ООО «Бирский комбинат молочных продуктов» | True | False | False | — / — | 0 / 0 | 0 / 0 | EXTERNAL_NEW | UNVERIFIED |
| `5320000979` | АО «Боровичский молочный завод» | True | False | False | — / — | 0 / 0 | 0 / 0 | EXTERNAL_NEW | UNVERIFIED |
| `5028002303` | ЗАО ЗСМ «Можайский» | True | False | False | — / — | 0 / 0 | 0 / 0 | EXTERNAL_NEW | UNVERIFIED |
| `5007126820` | ООО «ААП» | True | False | False | — / — | 0 / 0 | 0 / 0 | EXTERNAL_NEW | UNVERIFIED |
| `3128004452` | ЗАО МК «Авида» | True | False | False | — / — | 0 / 0 | 0 / 0 | EXTERNAL_NEW | UNVERIFIED |

## Status counts

- `CATEGORY_HISTORICAL`: 0
- `HISTORICAL_OTHER_CATEGORY`: 0
- `EXTERNAL_NEW`: 6
- `INVALID_INN`: 0

## Definitions

- **historical_universe:** Valid observed supplier_history relations with publish_date < as_of.
- **exact_category:** A historical relation to a lot containing the exact procurement_item.okpd2_code before as_of.
- **historical_lot_count:** Distinct historical lots for this supplier across all categories before as_of.
- **historical_win_count:** Distinct historical lots won by this supplier across all categories before as_of.
- **target_category_lot_count:** Distinct historical lots with this exact OKPD2 value and supplier relation before as_of.
- **target_category_win_count:** Distinct winning lots with this exact OKPD2 value before as_of.

## Performance

Six-candidate set-based reconciliation median: **5.331 ms** over three runs; EXPLAIN ANALYZE execution: **0.270 ms**. Indexes used: ix_history_supplier_date, ix_item_okpd2_code, procurement_lot_pkey, supplier_inn_key.

## Data quality findings

- None found in the six supplied INNs.

## Limitations

- Supplied company names are manual input and have not been independently verified.
- INN validity establishes identifier format and checksum only, not business identity, activity, or product scope.
- EXTERNAL_NEW means absent from observed canonical procurement history before as_of, not verified or absent from the market.
- AIS_GZ provides observed winner rows only; EM includes observed winner and non-winner rows.
- No external evidence was fetched, and no canonical enrichment rows were inserted.

## P3-002B handoff

Curate source records per candidate and product scope, then review their status and strength before any database ingestion. Keep reconciliation and verification decisions independent.
