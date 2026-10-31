"""Memory-only chart rendering for safe and repeatable EDA."""

from __future__ import annotations

import io
from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


@dataclass(frozen=True)
class Chart:
    title: str
    description: str
    png: bytes


def _png(fig: plt.Figure) -> bytes:
    buffer = io.BytesIO()
    try:
        fig.savefig(buffer, format="png", dpi=130, bbox_inches="tight")
        return buffer.getvalue()
    finally:
        plt.close(fig)


def create_charts(df: pd.DataFrame) -> list[Chart]:
    """Generate up to five lightweight charts; skip inappropriate features."""
    sampled = df.sample(n=min(len(df), 600), random_state=42) if len(df) > 600 else df
    numeric = []
    for col in sampled.select_dtypes(include="number").columns:
        finite = pd.to_numeric(sampled[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
        if finite.notna().sum() >= 3 and finite.nunique() >= 2:
            numeric.append(col)
    categorical = [col for col in sampled.select_dtypes(include=["object", "category", "bool"]).columns
                   if 2 <= sampled[col].nunique(dropna=True) <= 15]

    charts: list[Chart] = []
    if len(numeric) >= 2:
        corr = sampled[numeric[:8]].corr(numeric_only=True).dropna(axis=0, how="all").dropna(axis=1, how="all")
        if corr.shape[0] >= 2:
            fig, ax = plt.subplots(figsize=(7.5, 5.5))
            sns.heatmap(corr, cmap="vlag", center=0, annot=True, fmt=".2f", ax=ax, vmin=-1, vmax=1)
            ax.set_title("Feature correlation (Pearson)")
            charts.append(Chart("Correlation heatmap", "Pearson correlations between selected numerical features.", _png(fig)))

    for col in numeric[:2]:
        fig, ax = plt.subplots(figsize=(7.2, 4.5))
        vals = sampled[col].replace([np.inf, -np.inf], np.nan).dropna()
        sns.histplot(vals, kde=vals.nunique() > 2, ax=ax, bins="auto", color="#2563eb")
        ax.set_title(f"Distribution: {str(col)[:50]}")
        ax.set_xlabel(str(col)[:70])
        charts.append(Chart(f"Distribution — {str(col)[:50]}", "Histogram for a selected numeric feature.", _png(fig)))

    if categorical:
        col = categorical[0]
        counts = sampled[col].astype(str).value_counts().head(10)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        sns.barplot(x=counts.values, y=counts.index, ax=ax, color="#0f766e")
        ax.set_title(f"Top categories: {str(col)[:50]}")
        ax.set_xlabel("Count")
        ax.set_ylabel(str(col)[:70])
        charts.append(Chart("Category frequencies", "Most common non-missing categories.", _png(fig)))

    if len(numeric) >= 3:
        pair = sampled[numeric[:3]].replace([np.inf, -np.inf], np.nan).dropna().head(250)
        if len(pair) >= 8:
            graph = sns.pairplot(pair, corner=True, diag_kind="hist",
                                 plot_kws={"alpha": 0.55, "s": 13, "color": "#2563eb"},
                                 diag_kws={"color": "#2563eb"})
            graph.fig.suptitle("Pairwise feature relationships", y=1.03)
            charts.append(Chart("Pairplot", "Sampled pairwise relationships between three numeric features.", _png(graph.fig)))

    return charts
