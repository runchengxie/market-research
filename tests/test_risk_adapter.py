from __future__ import annotations

import pandas as pd
import pytest

from market_research.risk_adapter import (
    RISK_INPUT_SCHEMA_VERSION,
    build_a_share_risk_inputs,
    summarize_risk_input_coverage,
)


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2024-01-02"] * 4 + ["2024-01-03"] * 4,
            "symbol": ["A", "B", "C", "D"] * 2,
            "total_return": [0.01, 0.02, -0.01, 0.00, 0.02, 0.01, -0.02, 0.01],
            "market_cap": [10.0, 20.0, 30.0, 40.0] * 2,
            "quality": [1.0, 2.0, 3.0, 4.0] * 2,
            "industry": ["bank", "bank", "tech", "tech"] * 2,
            "pit_ok": [True] * 8,
        }
    )


def test_build_a_share_risk_inputs_returns_canonical_contract() -> None:
    inputs = build_a_share_risk_inputs(
        _panel(),
        ["market_cap", "quality"],
        industry_column="industry",
        pit_status_column="pit_ok",
    )
    assert inputs.exposures.index.names == ["as_of_date", "symbol"]
    assert inputs.returns.index.equals(inputs.exposures.index)
    assert inputs.metadata["schema_version"] == RISK_INPUT_SCHEMA_VERSION
    assert "industry_bank" in inputs.exposures.columns
    assert "industry_tech" in inputs.exposures.columns
    assert inputs.exposures["market_cap"].groupby(level="as_of_date").mean().abs().max() < 1e-12


def test_build_a_share_risk_inputs_preserves_raw_factor_scale_when_requested() -> None:
    inputs = build_a_share_risk_inputs(_panel(), ["market_cap"], standardize=False)
    assert inputs.exposures.loc[(pd.Timestamp("2024-01-02"), "A"), "market_cap"] == 10.0


def test_build_a_share_risk_inputs_rejects_non_pit_rows() -> None:
    panel = _panel()
    panel.loc[0, "pit_ok"] = False
    with pytest.raises(ValueError, match="PIT eligibility"):
        build_a_share_risk_inputs(panel, ["market_cap"], pit_status_column="pit_ok")


def test_build_a_share_risk_inputs_rejects_duplicate_keys() -> None:
    panel = pd.concat([_panel(), _panel().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build_a_share_risk_inputs(panel, ["market_cap"])


def test_summarize_risk_input_coverage_reports_factors_and_returns() -> None:
    from market_research.risk_adapter import AShareRiskInputs

    inputs = build_a_share_risk_inputs(_panel(), ["market_cap", "quality"])
    summary = summarize_risk_input_coverage(inputs)
    assert summary["dates"] == 2
    assert summary["symbols"] == 4
    assert summary["observations"] == 8
    assert summary["return_coverage"] == 1.0
    assert isinstance(inputs, AShareRiskInputs)
