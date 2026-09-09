from datetime import date
import sys
from types import SimpleNamespace

import pandas as pd

from market_research.markets.yahoo import (
    build_daily_shares_sidecar,
    jp_code_to_yahoo_symbol,
    symbols_pending_download,
)


def test_jp_code_maps_to_yahoo_symbol_without_check_digit():
    assert jp_code_to_yahoo_symbol("72030") == "7203.T"
    assert jp_code_to_yahoo_symbol("1301") == "1301.T"


def test_share_events_are_forward_filled_to_requested_trading_dates():
    events = pd.Series(
        [100, 120],
        index=pd.to_datetime(["2025-01-02", "2025-01-06"], utc=True),
    )

    result = build_daily_shares_sidecar(
        "72030",
        events,
        [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)],
    )

    assert result["shares_outstanding"].tolist() == [100, 100, 120]
    assert result["symbol"].tolist() == ["72030", "72030", "72030"]


def test_symbols_pending_download_skips_completed_parts():
    assert symbols_pending_download(["13010", "72030"], {"13010"}) == ["72030"]


def test_yfinance_sidecar_supports_resumable_parallel_downloads(tmp_path, monkeypatch):
    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def get_shares_full(self, start=None, end=None):
            return pd.Series(
                [100.0],
                index=pd.to_datetime(["2025-01-02"], utc=True),
            )

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=FakeTicker))
    from market_research.markets.yahoo import build_yfinance_shares_sidecar

    panel = pd.DataFrame(
        {
            "symbol": ["13010", "72030"],
            "date": [date(2025, 1, 2), date(2025, 1, 2)],
        }
    )

    result = build_yfinance_shares_sidecar(
        panel,
        tmp_path / "shares.parquet",
        parts_dir=tmp_path / "parts",
        workers=2,
    )

    assert sorted(result["symbol"].unique()) == ["13010", "72030"]
    assert len(list((tmp_path / "parts").glob("*.parquet"))) == 2
