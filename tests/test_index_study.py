import json

import pandas as pd
import pytest

from market_research.cli import main


def test_index_study_uses_common_dates_and_marks_missing_sources(tmp_path):
    prices = tmp_path / "prices.parquet"
    pd.DataFrame({
        "ts_code": ["932368.CSI"] * 3 + ["931082.CSI"] * 2,
        "trade_date": ["20250102", "20250103", "20250106", "20250103", "20250106"],
        "close": [100, 80, 88, 100, 120],
    }).to_parquet(prices)
    config = tmp_path / "study.json"
    output = tmp_path / "result"
    config.write_text(json.dumps({"sources": [str(prices)], "start": "2025-01-02", "end": "2025-01-06", "output_root": str(output)}))
    assert main(["report", "index-study", "--study", str(config)]) == 0
    result = pd.read_csv(output / "comparison.csv")
    row = result.loc[result.ts_code.eq("932368.CSI")].iloc[0]
    assert row.start == "2025-01-03"
    assert row.total_return == pytest.approx(.1)
    coverage = pd.read_csv(output / "coverage.csv")
    assert coverage.loc[coverage.ts_code.eq("883418.TI"), "status"].item() == "missing"
    assert str(tmp_path) not in (output / "report.html").read_text()


def test_index_study_rejects_conflicting_duplicate_prices(tmp_path):
    prices = tmp_path / "prices.parquet"
    pd.DataFrame({"ts_code": ["932368.CSI"] * 2, "trade_date": ["20250102"] * 2, "close": [100, 200]}).to_parquet(prices)
    config = tmp_path / "study.json"
    config.write_text(json.dumps({"sources": [str(prices)], "start": "2025-01-01", "end": "2025-01-06", "output_root": str(tmp_path / "out")}))
    with pytest.raises(ValueError, match="conflicting"):
        main(["report", "index-study", "--study", str(config)])
