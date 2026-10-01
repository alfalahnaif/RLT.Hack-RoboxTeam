"""Markdown rendering of reports/p2_001_semantic.json (+ feasibility and build facts). The JSON files are the source of truth."""
from __future__ import annotations

KEYS = ["candidate_winner_coverage", "candidate_observed_coverage", "winner_recall@1", "winner_recall@5", "winner_recall@10",
        "winner_recall@20", "winner_mrr", "ndcg@10", "ndcg@20", "candidates"]


def render(r: dict, feas: dict, build: dict) -> str:
    s0 = "S0 P2-003 (semantic off)"
    ch = r["chosen"]["name"]
    L = ["# P2-001 — Semantic Retrieval Candidate Expansion (DEV only)", "",
         f"> Ranking frozen at P2_003_RANKING. **HOLDOUT: not evaluated (sealed).** Labels are weak (unjudged ≠ irrelevant). "
         f"Model `{feas['model']['model']}` @ `{feas['model']['revision']}` ({feas['model']['dimension']}-d, {feas['model']['license']}).", "",
         f"**Decision: `{ch}`** — accepted by rules A–C: {r['accepted_abc']}; latency gate passed: {r['latency_gate_passed']}.", "",
         "## 1. Feasibility gate (run before any pgvector / full indexing)", "",
         f"- Rule: {feas['gate']['rule']} → **{feas['gate']['decision']}** ({feas['gate']['plausibly_recoverable']}/{feas['gate']['retrieval_failures']} "
         f"retrieval failures plausibly recoverable; by difficulty {feas['failures_by_difficulty']}).",
         f"- Corpus sample: {feas['corpus']['sample_size']:,} distinct texts visible before {feas['corpus']['visible_before']} "
         f"(full visible ≈ {feas['corpus']['full_visible_distinct_texts_estimate']:,}); success sample: "
         f"{feas['success_sample_plausibly_recoverable']}/{feas['success_sample_size']} winners also semantically reachable.",
         f"- Exact technical identifiers: on average {feas['technical_tokens']['mean_semantic_top10_containing_exact_token']} of the semantic top-10 "
         "neighbours contain the exact token → trigram/FTS stay responsible for model numbers.", "",
         "## 2. Semantic storage", "",
         "- Unit: one row per **distinct normalized product text** (`semantic_text`, md5 text hash, `first_seen_publish_date`, 384-d vector, "
         "model revision) mapped back to items through `md5(product_name_normalized)` (expression index with item date).",
         "- Temporal rule: text eligible only if `first_seen_publish_date < as_of`; every evidence item must itself have `publish_date < as_of` (SQL).",
         f"- pgvector {build.get('pgvector_version', '0.8.x')} in the `pgvector/pgvector:pg16` image; HNSW (cosine, m=16, ef_construction=64); "
         "query-time `hnsw.ef_search=200` with iterative scan (relaxed order).", "",
         "| Item | Value |", "|---|---:|"]
    for k in ("texts", "embedded", "embedding_seconds", "hnsw_build_seconds", "semantic_text_total_bytes", "hnsw_index_bytes",
              "item_md5_index_bytes", "database_bytes_before", "database_bytes"):
        if k in build:
            v = build[k]
            L.append(f"| {k} | {v / 2**20:,.0f} MiB |" if k.endswith("bytes") or k.endswith("bytes_before") else f"| {k} | {v:,} |")
    if ch != s0:
        c, c0 = r["configurations"][ch], r["configurations"][s0]
        cls = c["winner_pool_classification"]
        L += ["", f"> **Caveat.** Winner-pool movement vs S0: {cls['newly_recovered']} recovered, {cls['lost']} lost (semantic lots displace lexical "
              f"lots inside the historical-lot limit) → net +{cls['newly_recovered'] - cls['lost']} queries. Population-weighted coverage "
              f"{c0['weighted']['candidate_winner_coverage']} → {c['weighted']['candidate_winner_coverage']} (the lost queries carry higher stratum weight). "
              "Rule A is defined on unweighted coverage / MEDIUM+HARD recovery and was applied as declared."]
    L += ["", "## 3. Acceptance rule (declared before the results)", ""] + [f"- **{k}**: {v}" for k, v in r["acceptance_rule"].items()]
    L += ["", "## 4. Configurations (DEV, unweighted)", "",
          "| Configuration | Winner cov. | Obs. cov. | Cands | W-R@1 | W-R@5 | W-R@10 | W-R@20 | MRR | nDCG@10 | nDCG@20 | w-nDCG@10 | w-R@10 | Recovered (MED+HARD) | Δ cov. pp | Pool growth % |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for n, c in r["configurations"].items():
        u, w = c["unweighted"], c["weighted"]
        cls = c.get("winner_pool_classification", {})
        L.append(f"| {n} | {u['candidate_winner_coverage']} | {u['candidate_observed_coverage']} | {u['candidates']:.0f} | {u['winner_recall@1']} | "
                 f"{u['winner_recall@5']} | {u['winner_recall@10']} | {u['winner_recall@20']} | {u['winner_mrr']} | {u['ndcg@10']} | {u['ndcg@20']} | "
                 f"{w['ndcg@10']} | {w['winner_recall@10']} | {cls.get('newly_recovered', '—')} ({c.get('recovered_medium_hard', '—')}) | "
                 f"{c.get('coverage_gain_pp', '—')} | {c.get('candidate_pool_growth_pct', '—')} |")
    L += ["", "## 5. Weighted metrics (population-weighted by stratum_weight)", "", "| Metric | S0 | Chosen |", "|---|---:|---:|"]
    for k in KEYS:
        L.append(f"| {k} | {r['configurations'][s0]['weighted'][k]} | {r['configurations'][ch]['weighted'][k]} |")
    L += ["", "## 6. Difficulty breakdown (candidate coverage = retrieval; conditional recall in the configuration rows)", "",
          "| Difficulty | S0 coverage | Chosen coverage | S0 W-R@10 | Chosen W-R@10 |", "|---|---:|---:|---:|---:|"]
    for d in ("EASY", "MEDIUM", "HARD"):
        a, b = r["configurations"][s0]["by_difficulty"][d], r["configurations"][ch]["by_difficulty"][d]
        L.append(f"| {d} | {a['candidate_winner_coverage']} | {b['candidate_winner_coverage']} | {a['winner_recall@10']} | {b['winner_recall@10']} |")
    L += ["", "## 7. The 31 baseline retrieval failures under the chosen configuration", "", "| Query | Difficulty | Status | Detail |",
          "|---|---|---|---|"]
    for f in r["retrieval_failure_analysis"]:
        if f["status"] == "RECOVERED":
            ev = (f.get("semantic_evidence") or [{}])[0]
            det = f"winner rank {f.get('winner_rank')}; «{(ev.get('product') or '')[:70]}» cos {ev.get('cosine')} lot {ev.get('lot_id')} {ev.get('publish_date')}"
        else:
            det = f"{f.get('likely_reason')}" + (f" (best history cos {f['winner_best_history_cosine']})" if f.get("winner_best_history_cosine") else "")
        L.append(f"| {f['query_id']} | {f['difficulty']} | {f['status']} | {det} |")
    lat = r["latency"]
    L += ["", "## 8. Latency (end-to-end, warm, DEV, chosen)", "",
          f"p50 {lat['chosen']['p50_ms']} ms · p95 {lat['chosen']['p95_ms']} ms · max {lat['chosen']['max_ms']} ms · mean {lat['chosen']['mean_ms']} ms; "
          f"model load once per process: {lat['model_load_seconds_once_per_process']} s (cold start, not included in per-request numbers).",
          ""]
    bd = lat.get("breakdown")
    if bd:
        L += [f"Per-stage breakdown (fresh process, {bd['queries']} DEV queries; cold model load {bd['cold_model_load_seconds']} s is paid by the "
              f"first request of a process — first request total after load {bd['first_request_total_ms_after_model_load']} ms):", "",
              "| Stage | p50 ms | p95 ms | max ms | mean ms |", "|---|---:|---:|---:|---:|"]
        L += [f"| {k} | {v['p50']} | {v['p95']} | {v['max']} | {v['mean']} |" for k, v in bd["stages_warm"].items()]
        L.append("")
    L += ["## 9. Golden cases (after the freeze; not tuned on)", "", "| Lot | P2-003 rank | Now | Change |", "|---|---:|---:|---|"]
    for lot, g in r["golden_cases"].items():
        old, new = r["golden_p2_003_ranks"][lot], g["winner_rank"]
        L.append(f"| {lot} | {old} | {new} | {'better' if new and new < old else 'worse' if new is None or new > old else 'same'} |")
    L += ["", "## 10. Limitations", "",
          "- CPU-only embedding is slow on the team machine (~80–100 texts/s); the one-off build takes hours (resumable).",
          "- Cosine calibration (0.82 → 0, 0.95 → 1) is fixed from the feasibility study, not learned.",
          "- Semantic neighbours of generic texts are generic; recovered candidates can still rank low.",
          "- Failures caused by genuinely unseen suppliers cannot be fixed by any history-based retrieval (external expansion, P3).",
          "- Weak labels: an unobserved supplier is not proven irrelevant."]
    return "\n".join(L) + "\n"
