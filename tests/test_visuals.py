import pandas as pd

from insightflow.visuals import create_charts


def test_numeric_and_categorical_charts():
    df = pd.DataFrame({
        "price": list(range(20)),
        "quantity": list(range(20, 40)),
        "orders": list(range(40, 60)),
        "region": ["North", "South"] * 10,
    })
    charts = create_charts(df)
    titles = [c.title for c in charts]
    assert "Correlation heatmap" in titles
    assert "Category frequencies" in titles
    assert "Pairplot" in titles
    assert all(c.png.startswith(b"\x89PNG\r\n\x1a\n") for c in charts)
    assert len(charts) <= 5


def test_no_charts_with_constant_column():
    charts = create_charts(pd.DataFrame({"id": [1, 1, 1], "status": ["ok"] * 3}))
    assert charts == []


def test_visuals_not_crash_with_nans():
    df = pd.DataFrame({"a": [1.0, None, 3.0, 4.0], "b": [2.0, 3.0, None, 7.0]})
    assert len(create_charts(df)) >= 1
