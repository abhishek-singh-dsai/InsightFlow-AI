# Contributing

Thanks for improving InsightFlow AI. Please open an issue before large changes.

1. Fork and create a feature branch.
2. Install `pip install -e '.[dev]'` in a fresh Python 3.11+ environment.
3. Run `ruff check app.py src tests` and `pytest -q`.
4. Add unit tests for new analytics and edge cases.
5. Do not commit credentials, raw private datasets, or user-uploaded CSVs.

Use clear, focused pull requests. Avoid making causal claims from exploratory charts.
