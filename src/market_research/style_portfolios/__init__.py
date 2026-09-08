"""Reusable, market-evidence-only style portfolio calculations."""

from .cross_section import build_quantile_returns
from .diagnostics import analyze_tail_monotonicity, summarize_market_factor_evidence

__all__ = ["analyze_tail_monotonicity", "build_quantile_returns", "summarize_market_factor_evidence"]
