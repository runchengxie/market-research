import pandas as pd
import pytest

from market_research.studies.global_six_market.loader import load_daily_asset


def test_asset_loader_rejects_duplicate_dates(tmp_path):
    path = tmp_path / "asset.csv"
    pd.DataFrame({"date": ["2024-01-01", "2024-01-01"], "close": [1, 1], "volume": [1, 1]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="invalid or duplicate"):
        load_daily_asset(path, "US")
