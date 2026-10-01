# Canonical contracts — v0.2.0

JSON Schema **Draft 2020-12** contracts for the Supplier Radar canonical model (P1-001B, 2026-10-01).
Mapping from the organizer CSVs: [`docs/domain/DATA_MAPPING.md`](../docs/domain/DATA_MAPPING.md) · model summary: [`docs/domain/DOMAIN_MODEL.md` §0](../docs/domain/DOMAIN_MODEL.md).

| File | Entity |
|---|---|
| `common.schema.json` | shared `$defs` (UUID, INN, KPP, decimal string, platform, OKPD2 code, quality flags, source ref) |
| `procurement_lot.schema.json` | ProcurementLot (Извещения) |
| `procurement_item.schema.json` | ProcurementItem (ТРУ) |
| `supplier_history.schema.json` | SupplierHistory (Поставщики) |
| `supplier.schema.json` | Supplier (distinct INN) |
| `supplier_profile.schema.json` | SupplierProfile (curated enrichment) |
| `supplier_evidence.schema.json` | SupplierEvidence (provenance) |
| `source_mapping.json` | machine-readable source-column coverage |
| `fixtures/` | representative rows (real shapes, **masked identifiers**), enrichment examples, negative cases |

Validate: `python scripts/validate_contracts.py` (add `--raw data/raw` to also map and validate real rows).
The validator is stdlib-only (no JSON Schema library is installed) and rejects any keyword it does not implement.

Versioning (BR-25): PATCH = docs/clarification · MINOR = new optional field · MAJOR = breaking. Change procedure:
decision log → bump `version` in every touched schema → update fixtures → `validate_contracts.py` → rerun benchmark.
