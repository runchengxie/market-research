"""A-share adapters for the public risk-model input contract.

This module only normalizes caller-supplied, point-in-time panels.  Numerical
risk estimation lives in ``quant-platform``; this repository must remain free
of vendor clients, credentials, and private strategy data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

RISK_INPUT_SCHEMA_VERSION: Final[str] = "market-research.a-share-risk-inputs.v1"
_INDEX_NAMES: Final[tuple[str, str]] = ("as_of_date", "symbol")


@dataclass(frozen=True)
class AShareRiskInputs:
    """Canonical risk inputs plus provenance supplied by the caller."""

    exposures: pd.DataFrame
    returns: pd.Series
    metadata: dict[str, object]


def _cross_sectional_zscore(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().sum() < 2 or numeric.nunique(dropna=True) < 2:
        return numeric.astype(float)
    clipped = numeric.clip(numeric.quantile(0.01), numeric.quantile(0.99))
    standard_deviation = clipped.std(ddof=0)
    if not np.isfinite(standard_deviation) or standard_deviation == 0:
        return clipped.astype(float) * 0.0
    return (clipped - clipped.mean()) / standard_deviation


def build_a_share_risk_inputs(
    panel: pd.DataFrame,
    factor_columns: list[str] | tuple[str, ...],
    *,
    return_column: str = "total_return",
    date_column: str = "date",
    symbol_column: str = "symbol",
    industry_column: str | None = None,
    standardize: bool = True,
    pit_status_column: str | None = None,
) -> AShareRiskInputs:
    """Build PIT-aware exposure/return frames from a research panel.

    ``panel`` must already contain returns aligned to the intended holding
    interval. The adapter does not calculate forward returns, infer lag rules,
    or look up industry labels. If ``pit_status_column`` is supplied, every
    row used here must be explicitly marked ``True``.
    """

    if not isinstance(panel, pd.DataFrame):
        raise TypeError("panel must be a pandas DataFrame")
    factors = list(dict.fromkeys(factor_columns))
    if not factors:
        raise ValueError("factor_columns must contain at least one factor")
    required = {date_column, symbol_column, return_column, *factors}
    if industry_column is not None:
        required.add(industry_column)
    if pit_status_column is not None:
        required.add(pit_status_column)
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError("missing risk panel columns: " + ", ".join(sorted(missing)))

    frame = panel.copy()
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    if frame[date_column].isna().any():
        raise ValueError("risk panel contains invalid dates")
    if frame[[date_column, symbol_column]].duplicated().any():
        raise ValueError("risk panel contains duplicate (date, symbol) keys")
    if pit_status_column is not None and not frame[pit_status_column].astype(bool).all():
        raise ValueError("risk panel contains rows without explicit PIT eligibility")
    frame[return_column] = pd.to_numeric(frame[return_column], errors="coerce")
    if frame[return_column].isna().any() or not np.isfinite(frame[return_column]).all():
        raise ValueError("risk panel returns must be finite")

    exposure_columns: list[str] = []
    for factor in factors:
        frame[factor] = pd.to_numeric(frame[factor], errors="coerce")
        if standardize:
            frame[factor] = frame.groupby(date_column, sort=False)[factor].transform(
                _cross_sectional_zscore
            )
        exposure_columns.append(factor)

    if industry_column is not None:
        industry_values = frame[industry_column].astype("string").fillna("UNKNOWN")
        industry_dummies = pd.get_dummies(industry_values, prefix="industry", dtype=float)
        industry_dummies.index = frame.index
        frame = pd.concat([frame, industry_dummies], axis=1)
        exposure_columns.extend(industry_dummies.columns.tolist())

    keys = [date_column, symbol_column]
    exposures = frame.set_index(keys)[exposure_columns].sort_index()
    exposures.index = exposures.index.set_names(list(_INDEX_NAMES))
    returns = frame.set_index(keys)[return_column].sort_index()
    returns.index = returns.index.set_names(list(_INDEX_NAMES))
    returns.name = "total_return"
    metadata = {
        "schema_version": RISK_INPUT_SCHEMA_VERSION,
        "date_column": date_column,
        "symbol_column": symbol_column,
        "return_column": return_column,
        "factor_names": exposure_columns,
        "industry_column": industry_column,
        "standardized": standardize,
        "pit_status_column": pit_status_column,
        "coverage_start": exposures.index.get_level_values("as_of_date").min().date().isoformat(),
        "coverage_end": exposures.index.get_level_values("as_of_date").max().date().isoformat(),
        "observations": len(exposures),
    }
    return AShareRiskInputs(exposures, returns, metadata)


def summarize_risk_input_coverage(inputs: AShareRiskInputs) -> dict[str, object]:
    """Return coverage diagnostics without estimating a risk model."""

    if not isinstance(inputs, AShareRiskInputs):
        raise TypeError("inputs must be an AShareRiskInputs instance")
    exposures = inputs.exposures
    if not isinstance(exposures.index, pd.MultiIndex) or tuple(exposures.index.names) != _INDEX_NAMES:
        raise ValueError("inputs.exposures does not satisfy the risk input index contract")
    factor_coverage = {
        factor: float(exposures[factor].notna().mean()) for factor in exposures.columns
    }
    return {
        "schema_version": inputs.metadata.get("schema_version"),
        "dates": int(exposures.index.get_level_values("as_of_date").nunique()),
        "symbols": int(exposures.index.get_level_values("symbol").nunique()),
        "observations": len(exposures),
        "factor_coverage": factor_coverage,
        "return_coverage": float(inputs.returns.notna().mean()),
        "metadata": dict(inputs.metadata),
    }


def build_next_session_returns(
    panel: pd.DataFrame,
    *,
    price_column: str = "adj_close",
    date_column: str = "date",
    symbol_column: str = "symbol",
) -> pd.DataFrame:
    """Build formation-date to next-common-session returns without look-ahead.

    The returned ``total_return`` is labeled by the formation date. Rows are
    retained only when the symbol has a quote on the next common panel date;
    this makes missing next-session observations visible to coverage checks.
    """

    required = {date_column, symbol_column, price_column}
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError("panel missing return columns: " + ", ".join(sorted(missing)))
    frame = panel[[date_column, symbol_column, price_column]].copy()
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    frame[price_column] = pd.to_numeric(frame[price_column], errors="coerce")
    if frame[[date_column, symbol_column]].duplicated().any():
        raise ValueError("panel contains duplicate return keys")
    frame = frame.sort_values([symbol_column, date_column], kind="stable")
    dates = pd.Index(sorted(frame[date_column].dropna().unique()))
    next_dates = {dates[index]: dates[index + 1] for index in range(len(dates) - 1)}
    frame["next_date"] = frame.groupby(symbol_column)[date_column].shift(-1)
    frame["next_price"] = frame.groupby(symbol_column)[price_column].shift(-1)
    frame["expected_next_date"] = frame[date_column].map(next_dates)
    eligible = frame.loc[
        frame[price_column].gt(0)
        & frame["next_price"].gt(0)
        & frame["next_date"].eq(frame["expected_next_date"])
    ].copy()
    eligible["total_return"] = eligible["next_price"] / eligible[price_column] - 1.0
    return eligible[[date_column, symbol_column, "total_return"]].rename(
        columns={date_column: "as_of_date"}
    ).sort_values(["as_of_date", symbol_column], kind="stable").reset_index(drop=True)


__all__ = [
    "RISK_INPUT_SCHEMA_VERSION",
    "AShareRiskInputs",
    "build_a_share_risk_inputs",
    "build_next_session_returns",
    "summarize_risk_input_coverage",
]
