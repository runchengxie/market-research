import pandas as pd

from market_research.style_portfolios import analyze_tail_monotonicity, build_quantile_returns


def test_quantiles_are_lag_safe_and_tail_diagnostic_is_monotone():
    rows = []
    for date, prices in [("2024-01-01", {"a": 10, "b": 20, "c": 30, "d": 40}), ("2024-01-02", {"a": 11, "b": 21, "c": 30, "d": 39})]:
        for symbol, price in prices.items():
            rows.append({"date": date, "symbol": symbol, "market_cap": price, "factor": price, "adj_close": price})
    result = build_quantile_returns(pd.DataFrame(rows), "factor", quantiles=2)
    assert result["formation_date"].nunique() == 1
    assert analyze_tail_monotonicity(result)["tail_spread"] > 0


def test_invalid_panel_columns_are_rejected():
    try:
        build_quantile_returns(pd.DataFrame({"symbol": ["a"]}), "factor")
    except ValueError as exc:
        assert "missing panel columns" in str(exc)
    else:
        raise AssertionError("expected missing-column validation")
