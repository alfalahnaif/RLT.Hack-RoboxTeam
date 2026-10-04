# Supplier Radar README visual assets

These figures render **previously recorded results** from the repository, not new measurements. `metrics.json` preserves the values, source URLs, and source Git blob SHAs reviewed on 4 October 2026.

| Figure | Contents | Source |
|---|---|---|
| `dataset-scale-*` | Canonical counts by entity type; not a part-to-whole chart | `reports/ingestion_report.md` |
| `resolver-benchmark-*` | Fixed-test Resolver V4 percentages with the denominator for each metric | `reports/final_intelligence_integration.md` |
| `supplier-ranking-*` | Unweighted and population-weighted recall and rank-quality scores on the earlier frozen S3 HOLDOUT | `reports/p4_003_final_holdout.md` |

Each chart has light/dark SVG versions for README embedding and 150 dpi PNG versions for reuse in presentations. SVG typography is embedded as vector paths for consistent rendering. The README uses GitHub-supported `<picture>` elements to select a theme. PNG versions are optional and are not required by the README.

The full project logo already has two repository variants: `frontend/public/brand/logo.svg` has dark lettering for light backgrounds; `logo-light.svg` has white lettering for dark backgrounds. The README selects them without altering the logo artwork.

To regenerate from the recorded values:

```bash
python -m pip install matplotlib
python docs/assets/readme/generate_charts.py
```

Retain separate denominators. Do not interpret Resolver V4 precision as overall supplier-search accuracy. The later V4/Groq integration did not rerun the earlier frozen ranking HOLDOUT. The HOLDOUT report's confidence intervals for the reported overall baseline gains include zero.
