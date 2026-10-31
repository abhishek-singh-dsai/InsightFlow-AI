from pathlib import Path

import pandas as pd
import pytest

from insightflow.analysis import (
    DatasetError, dataset_profile, format_profile, load_csv,
)


def test_reads_csv(tmp_path: Path):
    f = tmp_path / "a.csv"
    f.write_text("qty,team\n5,alpha\n6,beta\n", encoding="utf-8-sig")
    data = load_csv(f)
    assert len(data) == 2
    assert list(data.columns) == ["qty", "team"]


def test_rejects_empty_file(tmp_path: Path):
    f = tmp_path / "a.csv"
    f.write_text("")
    with pytest.raises(DatasetError, match="empty"):
        load_csv(f)


def test_rejects_only_header(tmp_path: Path):
    f = tmp_path / "a.csv"
    f.write_text("x,y\n")
    with pytest.raises(DatasetError, match="no data"):
        load_csv(f)


def test_rejects_invalid_encoding(tmp_path: Path):
    f = tmp_path / "a.csv"
    f.write_bytes(b"a,b\n\xff,12\n")
    with pytest.raises(DatasetError, match="UTF-8"):
        load_csv(f)


def test_rejects_row_limit(tmp_path: Path, monkeypatch):
    import insightflow.analysis as mod
    monkeypatch.setattr(mod, "MAX_ROWS", 2)
    f = tmp_path / "a.csv"
    f.write_text("x\n1\n2\n3\n")
    with pytest.raises(DatasetError, match="rows"):
        load_csv(f)


def test_rejects_too_many_columns(tmp_path: Path, monkeypatch):
    import insightflow.analysis as mod
    monkeypatch.setattr(mod, "MAX_COLUMNS", 2)
    f = tmp_path / "a.csv"
    f.write_text("x,y,z\n1,2,3\n")
    with pytest.raises(DatasetError, match="columns"):
        load_csv(f)


def test_profile_correct_summary():
    df = pd.DataFrame({"revenue": [10, 20, None, 30], "region": ["A", "A", "B", "B"]})
    profile = dataset_profile(df)
    assert profile["shape"] == {"rows": 4, "columns": 2}
    assert profile["missing"]["revenue"] == 1
    assert profile["numeric_stats"]["revenue"]["mean"] == 20.0
    assert profile["top_categories"]["region"] == {"A": 2, "B": 2}
    assert "Numeric feature summary" in format_profile(profile)


def test_profile_duplicate_rows():
    profile = dataset_profile(pd.DataFrame({"x": [1, 1, 2]}))
    assert profile["duplicates"] == 1


def test_profile_no_numeric():
    profile = dataset_profile(pd.DataFrame({"x": ["A", "B"]}))
    assert profile["numeric_stats"] == {}
    assert "No numeric features" in format_profile(profile)


def test_profile_handles_infinity():
    profile = dataset_profile(pd.DataFrame({"x": [1, float("inf"), 3]}))
    assert profile["numeric_stats"]["x"]["mean"] == 2.0


def test_rejects_duplicate_csv_headers(tmp_path: Path):
    f = tmp_path / "dups.csv"
    f.write_text("x,x\n1,2\n")
    with pytest.raises(DatasetError, match="Duplicate"):
        load_csv(f)


def test_rejects_missing_path(tmp_path: Path):
    with pytest.raises(DatasetError, match="not be found"):
        load_csv(tmp_path / "missing.csv")


def test_rejects_oversized_file(tmp_path: Path, monkeypatch):
    import insightflow.analysis as mod
    monkeypatch.setattr(mod, "MAX_UPLOAD_BYTES", 8)
    f = tmp_path / "large.csv"
    f.write_text("col\n12345678\n")
    with pytest.raises(DatasetError, match="10 MB"):
        load_csv(f)
