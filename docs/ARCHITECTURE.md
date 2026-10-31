# Architecture and design decisions

## Data path

1. Chainlit requests one UTF-8 CSV upload (maximum 10 MB).
2. `analysis.load_csv` validates format, dimensions, and data presence. Uploaded content is treated as data, not executable code.
3. `analysis.dataset_profile` computes bounded descriptive statistics with Pandas.
4. `visuals.create_charts` samples up to 600 rows to generate chart PNG bytes, avoiding leaked temporary chart files.
5. `app.py` displays local statistics and charts before any optional AI call.
6. With a Gemini key, `ai.py` submits a bounded JSON profile to Gemini for narrative interpretation. Up to two selected charts are also submitted for optional image interpretation.
7. Questions are answered from aggregates only. The app cannot accurately answer arbitrary row-specific questions and is not advertised as a natural-language query engine.

## Design tradeoffs

| Decision | Benefit | Limitation |
| --- | --- | --- |
| Deterministic Pandas-first statistics | Clear separation between measurement and AI opinion | Covers only conventional EDA summaries |
| Bounded, sampled chart generation | Lower latency and memory use | Chart shape may differ from full dataset |
| No mandatory API key | Usable locally without external services | AI insight features unavailable in this mode |
| Only aggregated statistics sent as text | Limits exposure of full row-level records | Category labels and chart pixels may still disclose data |
| Tests run with no network or API key | Reproducible on GitHub Actions | Gemini API and Chainlit browser experience need separate live verification |

## Security posture

This is an educational analytics prototype, **not** a production data-management service. It does not include user authentication, tenancy, auditing, or a retention policy for framework-managed uploads. Avoid sensitive data, particularly when activating Gemini. Actual API keys must never be committed. CSV contents cannot grant elevated privileges; the application does not evaluate CSV formulas or execute user-supplied Python.

## Responsible interpretation

Exploratory correlations are descriptive, not causal. Visual samples do not replace full-dataset summary statistics. AI output must be checked against computed facts; limitations are explicitly described in prompts and documentation.
