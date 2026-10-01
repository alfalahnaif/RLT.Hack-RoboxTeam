# P3-001 Supplier Pool Health — real-data analysis

As of **2026-01-01** (strictly earlier publish dates); recent window **365 days**.
Source: canonical `procurement_lot`, `procurement_item`, `supplier_history`, `supplier` only.

## Metric definitions

- A category lot counts once even when it has repeated matching items; procurements are distinct procedure IDs and customers are distinct known/non-null customer INNs.
- An observed supplier has a valid historical relation. AIS_GZ supplies observed winner rows only; EM supplies observed winner and non-winner rows. AIS_GZ is never treated as a complete participant list.
- A winning supplier has at least one `is_winner=true` relation. An award is one distinct `(lot_id, supplier_id)` winning relation; it is not a monetary share.
- A recent winning supplier has at least one winning relation with publish date in `[as_of - recent_days, as_of)`.
- Top-one and top-three shares use award counts. HHI = Σ(awards for supplier / total awards)², on a 0–1 scale.
- Winning alternatives are other historical winners; observed-only alternatives have EM non-winning evidence but no award in this scope. No recommendation score is used.

## Dataset distribution

**8,452** distinct observed OKPD2 values as represented in the source dataset (mixed depths); **8,354** with awards; **2,896** pass the support rule.

| Metric | Population | p25 | p50 | p75 | p90 | p95 |
|---|---|---:|---:|---:|---:|---:|
| lot_count | All with awards | 2.0 | 8.0 | 44.0 | 236.0 | 608.7 |
| award_count | All with awards | 2.0 | 7.0 | 39.0 | 207.0 | 538.35 |
| observed_supplier_count | All with awards | 3.0 | 9.0 | 35.0 | 102.0 | 192.35 |
| winning_supplier_count | All with awards | 2.0 | 5.0 | 22.0 | 66.0 | 127.0 |
| top1_share | All with awards | 0.1538 | 0.3333 | 0.6667 | 1.0 | 1.0 |
| top3_share | All with awards | 0.3529 | 0.7 | 1.0 | 1.0 | 1.0 |
| hhi | All with awards | 0.0816 | 0.2278 | 0.5556 | 1.0 | 1.0 |
| lot_count | Eligible | 41.0 | 88.5 | 297.5 | 885.5 | 1618.5 |
| award_count | Eligible | 36.0 | 80.0 | 263.25 | 776.0 | 1493.75 |
| observed_supplier_count | Eligible | 32.0 | 56.0 | 117.0 | 248.0 | 360.0 |
| winning_supplier_count | Eligible | 21.0 | 37.0 | 77.0 | 168.5 | 250.5 |
| top1_share | Eligible | 0.0846 | 0.1351 | 0.2223 | 0.3497 | 0.4444 |
| top3_share | Eligible | 0.2 | 0.2951 | 0.44 | 0.6094 | 0.7267 |
| hhi | Eligible | 0.0321 | 0.0559 | 0.1001 | 0.1807 | 0.2632 |

## Analytical thresholds

Minimum support: **20 lots and 20 observed awards**; otherwise `INSUFFICIENT_DATA`.
The all-awarded median is 8 lots and 7 awards; 20/20 avoids confident labels for the small-category majority while retaining 2,896 categories.
Among eligible categories, p75 top-one = 22.2% and p75 HHI = 0.1001; p95 top-one = 44.4% and p95 HHI = 0.2632.
Thresholds are product analytics, not legal or competition-law thresholds. The label is the highest tier met by **either** indicator:

| Label | Top-one share | HHI |
|---|---:|---:|
| MODERATE | ≥ 25% | ≥ 0.125 |
| HIGH | ≥ 50% | ≥ 0.320 |
| VERY_HIGH | ≥ 80% | ≥ 0.600 |
| LOW | below both MODERATE boundaries | |

## Category counts

| Label | Observed OKPD2 categories |
|---|---:|
| INSUFFICIENT_DATA | 5,556 |
| LOW | 2,250 |
| MODERATE | 530 |
| HIGH | 85 |
| VERY_HIGH | 31 |

## Demo category cards

Selection: sterilized milk and natural canned fish have comparable activity (182 vs 179 lots), familiar source product descriptions, and sharply different award concentration. Cranberry is a second high-concentration example with 227 lots. Selection does not use recommendation performance.

### Primary: `10.51.11.141` — VERY_HIGH

Representative source product: Молоко питьевое стерилизованное 2,5 % жирности длительного хранения.
182 lots · 182 procurements · 39 customers · 173 observed awards · 5 winning suppliers · 6 observed suppliers.
Top one 94.2% · top three 98.8% · HHI 0.889.
Dominant supplier `7804471404`: 163 observed awards. Historical alternatives: 5 total (4 winners, 1 observed-only).

### Contrast: `10.20.25.111` — LOW

Representative source product: Консервы рыбные натуральные.
179 lots · 179 procurements · 74 customers · 169 observed awards · 42 winning suppliers · 45 observed suppliers.
Top one 13.0% · top three 29.0% · HHI 0.049.
Dominant supplier `7806410527`: 22 observed awards. Historical alternatives: 44 total (41 winners, 3 observed-only).

### Backup: `01.25.19.150` — VERY_HIGH

Representative source product: Клюква тип 1.
227 lots · 227 procurements · 73 customers · 219 observed awards · 15 winning suppliers · 16 observed suppliers.
Top one 88.1% · top three 92.7% · HHI 0.778.
Dominant supplier `7817306535`: 193 observed awards. Historical alternatives: 15 total (14 winners, 1 observed-only).

## Reconciliation of known categories

| Code | Lots | Winners | Top one | Top three | HHI | Label |
|---|---:|---:|---:|---:|---:|---|
| 10.51.11.141 | 182 | 5 | 94.2% | 98.8% | 0.889 | VERY_HIGH |
| 01.25.19.150 | 227 | 15 | 88.1% | 92.7% | 0.778 | VERY_HIGH |
| 10.61.22.130 | 136 | 9 | 86.4% | 90.9% | 0.748 | VERY_HIGH |
| 10.39.17.111 | 337 | 12 | 38.7% | 75.7% | 0.247 | MODERATE |

## Other supported categories

Top historical concentration among categories with at least 100 lots and 100 awards:

| Code | Lots | Winners | Top one | HHI |
|---|---:|---:|---:|---:|
| 49.31.21.140 | 444 | 2 | 96.3% | 0.929 |
| 62.02 | 116 | 6 | 95.7% | 0.915 |
| 10.51.11.141 | 182 | 5 | 94.2% | 0.889 |
| 58.19.14.110 | 138 | 9 | 91.5% | 0.839 |
| 01.25.19.150 | 227 | 15 | 88.1% | 0.778 |
| 10.61.22.130 | 136 | 9 | 86.4% | 0.748 |
| 35.12.10.120 | 262 | 19 | 83.4% | 0.699 |
| 53.10.12.000 | 204 | 13 | 81.3% | 0.669 |
| 10.86.10.990 | 152 | 16 | 81.1% | 0.662 |
| 61.10.12.000 | 160 | 4 | 78.3% | 0.642 |

Lower concentration comparisons with 100–1,000 lots and at least 20 winning suppliers:

| Code | Lots | Winners | Top one | HHI |
|---|---:|---:|---:|---:|
| 85.21.12.000 | 949 | 536 | 1.3% | 0.003 |
| 82.11.10.000 | 717 | 470 | 3.1% | 0.004 |
| 28.99.39.190 | 610 | 338 | 2.2% | 0.004 |
| 90.01.10.000 | 502 | 313 | 2.3% | 0.005 |
| 26.51.51.110 | 866 | 331 | 2.5% | 0.007 |
| 25.94.12.190 | 542 | 261 | 3.0% | 0.007 |
| 43.22.12.190 | 779 | 337 | 3.2% | 0.007 |
| 23.12.13.110 | 575 | 256 | 2.5% | 0.008 |
| 27.90.40.190 | 464 | 259 | 3.2% | 0.008 |
| 26.20.40.110 | 805 | 323 | 3.3% | 0.008 |

## Performance

Full distribution query: **29.20 s** for 8,452 codes.
- single_code: median service latency **26.18 ms** (three runs); EXPLAIN ANALYZE execution **24.87 ms**, plan root `Result`.
- group: median service latency **260.22 ms** (three runs); EXPLAIN ANALYZE execution **232.51 ms**, plan root `Result`.
Existing indexes supported interactive single-code and group analysis in this run; the full distribution is a batch report. No new index or migration was added.

## Limitations

- Historical procurement concentration does not establish current market concentration.
- Procurement records do not cover the entire supplier market.
- AIS_GZ provides observed winner rows only; EM contains observed winner and non-winner rows.
- Observed EM non-winners do not establish a complete participant or market population.
- Supplier registration region does not establish delivery capability.
- External supplier expansion is a separate stage.
- Labels are Supplier Radar analytical categories, not legal classifications.

## Integration note

Call `app.analytics.pool_health.analyze_pool(connection, PoolScope(...), PoolThresholds(...))` from a later CLI/API change after parallel search work is merged. The current script is read-only and independent.
