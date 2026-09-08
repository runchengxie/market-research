import pandas as pd
import pytest


def test_index_price_snapshot_uses_requested_endpoints():
    from market_research.index_research import build_index_price_snapshot

    daily = pd.DataFrame(
        {
            "ts_code": ["000300.SH"] * 3,
            "trade_date": ["20260102", "20260105", "20260106"],
            "close": [100.0, 110.0, 121.0],
        }
    )
    result = build_index_price_snapshot(daily, start_date="20260102", end_date="20260106")

    assert result.loc[0, "price_return"] == pytest.approx(0.21)
    assert result.loc[0, "cagr"] == pytest.approx(0.21 ** 0.1 if False else 1.21 ** 0.1 - 1)


def test_etf_pairing_matches_longest_benchmark_name():
    from market_research.index_research import build_etf_index_pairing

    etf = pd.DataFrame(
        {
            "ts_code": ["510001.SH"], "name": ["示例ETF"], "benchmark": ["中证500信息技术指数×100%"],
            "status": ["L"], "fund_type": ["股票型"], "list_date": [20200101],
        }
    )
    catalog = pd.DataFrame({"ts_code": ["000905.SH", "931087.CSI"], "indx_name": ["中证500指数", "中证500信息技术指数"]})

    result = build_etf_index_pairing(etf, catalog, start_date=20210101)

    assert result.loc[0, "matched_index_name"] == "中证500信息技术指数"
    assert result.loc[0, "index_ts_code"] == "931087.CSI"


def test_cashflow_snapshot_prefers_total_return_and_marks_missing_history():
    from market_research.index_research import build_cashflow_snapshot

    raw = pd.DataFrame(
        {
            "ts_code": ["932365.CSI", "932365CNY010.CSI"] * 3,
            "trade_date": ["20250102", "20250102", "20260102", "20260102", "20260105", "20260105"],
            "close": [100, 101, 110, 111, 112, 113],
        }
    )
    result = build_cashflow_snapshot(raw, indexes=(("932365.CSI", "现金流", "CSI", "quarterly", "note"),))

    assert set(result) == {"performance", "status", "rebalance_frequency"}
    assert result["performance"].loc[0, "return_basis"] == "gross_total_return"
    assert result["status"].loc[0, "status"] == "available"


def test_index_code_routes_to_provider_and_pair_metrics_are_deterministic():
    from market_research.index_research import api_for_index_code, build_etf_index_metrics

    assert api_for_index_code("801001.SI") == "sw_daily"
    assert api_for_index_code("000300.SH") == "index_daily"
    etf = pd.DataFrame({"ts_code": ["510001.SH"] * 2, "trade_date": ["20260102", "20260106"], "adj_close": [100, 110], "amount": [1000, 2000]})
    index = pd.DataFrame({"ts_code": ["000300.SH"] * 2, "trade_date": ["20260102", "20260106"], "close": [100, 105]})
    result = build_etf_index_metrics(etf, index, "510001.SH", "000300.SH", "20260102", "20260106")
    assert result["etf_total_return"] == pytest.approx(0.1)
    assert result["index_price_return"] == pytest.approx(0.05)
