from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Final

import pandas as pd


CANONICAL_COLUMNS: Final[tuple[str, ...]] = (
    "market",
    "symbol",
    "date",
    "close",
    "volume",
    "turnover",
    "market_cap",
    "currency",
    "is_tradable",
    "is_suspended",
    "source",
)
SUPPORTED_CURRENCIES: Final[frozenset[str]] = frozenset({"CNY", "HKD", "USD", "JPY"})
REQUIRED_METADATA_FIELDS: Final[tuple[str, ...]] = (
    "source",
    "as_of",
    "currency",
    "universe_filter",
    "fx_method",
    "feature_lag",
    "coverage_start",
    "coverage_end",
    "calendar_mode",
    "quality_status",
)


@dataclass(frozen=True)
class PanelMetadata:
    source: str
    as_of: str
    currency: str
    universe_filter: str
    fx_method: str
    feature_lag: int
    coverage_start: str | None
    coverage_end: str | None
    calendar_mode: str
    quality_status: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_panel(frame: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    missing = [column for column in CANONICAL_COLUMNS if column not in frame.columns]
    if missing:
        issues.append("missing_columns:" + ",".join(missing))
        return issues

    if frame.duplicated(list(("market", "symbol", "date"))).any():
        issues.append("duplicate_key")
    if not bool(frame["currency"].dropna().isin(SUPPORTED_CURRENCIES).all()):
        issues.append("invalid_currency")
    for column in ("close", "volume", "turnover", "market_cap"):
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.notna().any() and not values[values.notna()].map(pd.api.types.is_number).all():
            issues.append(f"invalid_numeric:{column}")
    return issues


def normalize_panel(frame: pd.DataFrame, metadata: PanelMetadata) -> tuple[pd.DataFrame, PanelMetadata]:
    if metadata.currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unsupported currency: {metadata.currency}")
    missing = [field for field in REQUIRED_METADATA_FIELDS if not getattr(metadata, field, None) and field != "feature_lag"]
    if missing:
        raise ValueError("missing metadata: " + ",".join(missing))
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.date
    for column in ("close", "volume", "turnover", "market_cap"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    issues = validate_panel(result)
    if issues:
        raise ValueError("invalid panel: " + ",".join(issues))
    result = result.loc[:, list(CANONICAL_COLUMNS)].sort_values(
        ["market", "symbol", "date"], kind="stable"
    ).reset_index(drop=True)
    return result, metadata
