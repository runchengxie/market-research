"""Research-only six-market ETF proxy allocation study."""

from .loader import load_daily_asset, load_distributions, load_fx_series, validate_common_history
from .portfolio import build_month_end_calendar, compute_usd_return_components, summarize_portfolio

__all__ = [
    "build_month_end_calendar",
    "compute_usd_return_components",
    "load_daily_asset",
    "load_distributions",
    "load_fx_series",
    "summarize_portfolio",
    "validate_common_history",
]
