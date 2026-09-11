from __future__ import annotations

from pathlib import Path

import pandas as pd


def _date_parameter(value: str) -> str:
    text = str(value)
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return pd.Timestamp(text).date().isoformat()


def load_historical_turnover_panel(
    daily_root: Path,
    daily_basic_root: Path,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Join the 2008+ raw daily and daily-basic sources for turnover research.

    The historical source has no reliable ST or suspension flags, so the result
    is deliberately marked incomplete and must not be treated as equivalent to
    the clean 2015+ A-share panel.
    """
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("DuckDB is required for historical turnover loading") from exc

    daily_path = Path(daily_root)
    basic_path = Path(daily_basic_root)
    if not daily_path.exists() or not basic_path.exists():
        raise RuntimeError("historical daily and daily_basic roots are required")

    filters = ["d.date IS NOT NULL", "b.date IS NOT NULL", "d.amount > 0", "b.total_mv > 0"]
    parameters: list[object] = [str(daily_path / "**" / "*.parquet"), str(basic_path / "**" / "*.parquet")]
    if start_date is not None:
        filters.append("d.date >= CAST(? AS DATE)")
        parameters.append(_date_parameter(start_date))
    if end_date is not None:
        filters.append("d.date <= CAST(? AS DATE)")
        parameters.append(_date_parameter(end_date))

    query = f"""
        WITH daily AS (
            SELECT ts_code,
                   COALESCE(try_cast(trade_date AS DATE), try_strptime(CAST(trade_date AS VARCHAR), '%Y%m%d')) AS date,
                   CAST(amount AS DOUBLE) AS amount
            FROM read_parquet(?, union_by_name=true)
        ), daily_basic AS (
            SELECT ts_code,
                   COALESCE(try_cast(trade_date AS DATE), try_strptime(CAST(trade_date AS VARCHAR), '%Y%m%d')) AS date,
                   CAST(total_mv AS DOUBLE) AS total_mv
            FROM read_parquet(?, union_by_name=true)
        )
        SELECT 'a_share' AS market,
               d.ts_code AS symbol,
               CAST(d.date AS DATE) AS date,
               d.amount * 1000 AS turnover,
               b.total_mv * 10000 AS market_cap,
               'CNY' AS currency,
               'historical daily + daily_basic' AS source
        FROM daily d
        INNER JOIN daily_basic b USING (ts_code, date)
        WHERE {' AND '.join(filters)}
        ORDER BY d.date, d.ts_code
    """
    connection = duckdb.connect()
    try:
        frame = connection.execute(query, parameters).fetchdf()
    finally:
        connection.close()

    if not frame.empty:
        frame["date"] = pd.to_datetime(frame["date"]).dt.date.astype(str)
    metadata = {
        "source": "Tushare A-share historical daily + daily_basic",
        "as_of": str(frame["date"].max()) if not frame.empty else end_date or "",
        "currency": "CNY",
        "universe_filter": "positive amount/market cap; historical ST and suspension flags unavailable",
        "feature_lag": 1,
        "coverage_start": str(frame["date"].min()) if not frame.empty else None,
        "coverage_end": str(frame["date"].max()) if not frame.empty else None,
        "calendar_mode": "observed_daily",
        "quality_status": "incomplete",
    }
    return frame, metadata
