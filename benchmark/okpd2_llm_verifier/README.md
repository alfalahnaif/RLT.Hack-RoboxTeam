# OKPD2 verifier validation

`validation.json` contains four hand-labeled, ambiguous resolver-contract fixtures. Candidate codes and titles are taken from the checked-in OKPD2 category index. These are **not** observations from a running Resolver V4 or a live language model. The sealed supplier-ranking HOLDOUT is not read.

Run the replay to verify the evaluation pipeline:

```powershell
$env:PYTHONPATH='backend'
python -m app.search.llm_benchmark --input benchmark/okpd2_llm_verifier/validation.json --mode fixture-replay
```

For a live Groq run, put the following settings in a Git-ignored `.env` in this worktree (never paste or commit the key):

```text
OKPD2_LLM_BASE_URL=https://api.groq.com/openai/v1
OKPD2_LLM_MODEL=qwen/qwen3.8-27b
OKPD2_LLM_API_KEY=<secret>
OKPD2_LLM_TIMEOUT_SECONDS=2.0
```

Then run only this benchmark:

```powershell
$env:PYTHONPATH='backend'
python -m app.search.llm_benchmark --input benchmark/okpd2_llm_verifier/validation.json --mode live
```

The runner reads only verifier settings from `.env`, never prints the key, and reports provider connection, exact model ID, strict JSON Schema response validation, p50/p95 verification latency, timeout rate, invalid-response rate, and each fixture decision. It also computes the requested comparison metrics. Replace the fixture's deterministic results with outputs collected from the completed Resolver V4 before treating these figures as product performance. Never use fixture results as final model accuracy.

The verifier is disabled in supplier search by default. Set `OKPD2_LLM_VERIFIER_ENABLED=1` to enable it. `OKPD2_LLM_TIMEOUT_SECONDS` defaults to 0.65 and is capped at 2 seconds. `app.search.llm_verifier.metrics_snapshot()` reports process-local call rate, p50/p95 latency, and timeout rate. Audit records use the `okpd2_llm_verification` logger event with candidate codes and names, decision, selected code, short reason, provider/model, latency, and fallback state. Logs should be handled according to procurement query retention policy.
