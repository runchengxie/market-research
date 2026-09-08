from datetime import date

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
