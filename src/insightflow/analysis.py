"""Bounded, deterministic CSV loading and exploratory statistics."""

from __future__ import annotations

from pathlib import Path
import csv
from typing import Any

import numpy as np
import pandas as pd

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 100


class DatasetError(ValueError):
    """Raise for invalid or unsupported CSV uploads."""


def load_csv(path: str | Path) -> pd.DataFrame:
    """Read a small UTF-8 CSV and reject unsafe/unsupported sizes and shapes.

    File size is checked before reading and row/column limits are enforced on
    the parsed result. The application never runs code found inside a CSV.
    """
    path = Path(path)
    if not path.is_file():
        raise DatasetError("The uploaded CSV could not be found.")
    if path.stat().st_size > MAX_UPLOAD_BYTES:
        raise DatasetError("CSV exceeds the 10 MB upload limit.")
    if not path.stat().st_size:
        raise DatasetError("CSV is empty.")

    try:
        # Validate the *original* CSV header. pandas otherwise silently renames duplicate names.
        with path.open(encoding="utf-8-sig", newline="") as handle:
            csv.field_size_limit(2_000_000)
            header = next(csv.reader(handle), [])
        if len(header) > MAX_COLUMNS:
            raise DatasetError(f"CSV exceeds {MAX_COLUMNS} columns.")
        if len(header) != len(set(header)):
            raise DatasetError("Duplicate column names are not supported.")
        # Only load bounded rows/columns; an extra row/column detects over-limit input.
        data = pd.read_csv(
            path, encoding="utf-8-sig", nrows=MAX_ROWS + 1,
            on_bad_lines="error", low_memory=False,
        )
    except DatasetError:
        raise
    except (UnicodeError, csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise DatasetError("Unable to parse UTF-8 CSV. Check the delimiter and file encoding.") from exc

    if data.empty:
        raise DatasetError("CSV has no data rows.")
    if len(data) > MAX_ROWS:
        raise DatasetError(f"CSV exceeds {MAX_ROWS:,} rows.")
    if len(data.columns) > MAX_COLUMNS:
        raise DatasetError(f"CSV exceeds {MAX_COLUMNS} columns.")
    if data.columns.duplicated().any():
        raise DatasetError("Duplicate column names are not supported.")
    return data


def _native(value: Any) -> Any:
    """Convert numpy scalars to JSON-safe primitives; replace NaN/inf with None."""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return round(float(value), 4) if np.isfinite(value) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if pd.isna(value):
        return None
    return str(value)


def dataset_profile(df: pd.DataFrame) -> dict[str, Any]:
    """Return reproducible aggregates for the UI and bounded AI context."""
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    shape = {"rows": int(len(df)), "columns": int(len(df.columns))}

    numeric_stats = {}
    for col in numeric[:12]:
        values = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if not values.empty:
            numeric_stats[str(col)[:120]] = {
                "count": int(values.count()),
                "mean": _native(values.mean()),
                "median": _native(values.median()),
                "min": _native(values.min()),
                "max": _native(values.max()),
                "std": _native(values.std()) if len(values) > 1 else None,
            }

    top_categories = {}
    for col in categorical[:8]:
        counts = df[col].dropna().astype(str).value_counts().head(5)
        top_categories[str(col)[:120]] = {
            str(k)[:64]: int(v) for k, v in counts.items()
        }

    missing = {str(k)[:120]: int(v) for k, v in df.isna().sum().items() if int(v) > 0}
    return {
        "shape": shape,
        "duplicates": int(df.duplicated().sum()),
        "missing": missing,
        "dtypes": {str(k)[:120]: str(v) for k, v in df.dtypes.items()},
        "numeric_stats": numeric_stats,
        "top_categories": top_categories,
        "numeric_columns": [str(c) for c in numeric[:12]],
        "categorical_columns": [str(c) for c in categorical[:8]],
    }


def format_profile(profile: dict[str, Any]) -> str:
    rows = profile["shape"]["rows"]
    cols = profile["shape"]["columns"]
    missing = profile["missing"]
    lines = [
        "### Dataset health",
        f"- **Rows:** {rows:,} · **Columns:** {cols}",
        f"- **Duplicate rows:** {profile['duplicates']:,}",
        f"- **Missing cells:** {sum(missing.values()):,}",
        "",
        "### Numeric feature summary",
    ]
    if not profile["numeric_stats"]:
        lines.append("No numeric features detected.")
    else:
        lines.append("| Column | Count | Mean | Median | Min | Max |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for col, s in profile["numeric_stats"].items():
            safe_col = col.replace("|", "\\|").replace("`", "")
            lines.append(f"| {safe_col} | {s['count']} | {s['mean']} | {s['median']} | {s['min']} | {s['max']} |")
    if missing:
        lines.extend(["", "### Missing values (per column)"])
        lines.extend(f"- `{str(k).replace('`', '')}`: {v:,}" for k, v in list(missing.items())[:15])
    return "\n".join(lines)
