from __future__ import annotations

import pandas as pd


def reconstruct_smallest_cap_index(
    panel: pd.DataFrame, constituent_count: int = 400
) -> pd.DataFrame:
    if constituent_count <= 0:
        raise ValueError("constituent_count must be positive")
    frame = panel.loc[panel["market"].eq("a_share")].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["adj_close"] = pd.to_numeric(frame.get("adj_close", frame["close"]), errors="coerce")
    frame["market_cap"] = pd.to_numeric(frame["market_cap"], errors="coerce")
    frame["is_st"] = frame.get("is_st", False)
    frame["is_suspended"] = frame.get("is_suspended", False)
    frame = frame.sort_values(["symbol", "date"], kind="stable")
    frame["next_date"] = frame.groupby("symbol")["date"].shift(-1)
    frame["next_adj_close"] = frame.groupby("symbol")["adj_close"].shift(-1)
    dates = sorted(frame["date"].dropna().unique())
    next_dates = {current: following for current, following in zip(dates, dates[1:])}
    frame["next_market_date"] = frame["date"].map(next_dates)
    eligible = frame.loc[
        ~frame["is_st"].astype(bool)
        & ~frame["is_suspended"].astype(bool)
        & frame["market_cap"].gt(0)
        & frame["adj_close"].gt(0)
    ].copy()
    eligible["rank"] = eligible.groupby("date")["market_cap"].rank(method="first", ascending=True)
    selected = eligible.loc[eligible["rank"] <= constituent_count].copy()
    selected["valid_next"] = (
        selected["next_date"].eq(selected["next_market_date"])
        & selected["next_adj_close"].gt(0)
    )
    result = (
        selected.groupby(["date", "next_market_date"], as_index=False)
        .agg(
            selected_count=("symbol", "size"),
            priced_count=("valid_next", "sum"),
        )
    )
    return _calculate_returns(selected, result)


def reconstruct_smallest_cap_index_from_parquet(
    data_root: str | object, constituent_count: int = 400,
    start_date: str | None = None, end_date: str | None = None,
) -> pd.DataFrame:
    """Run the A-share reconstruction inside DuckDB for large Parquet roots."""
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("DuckDB is required for parquet index reconstruction") from exc
    from pathlib import Path

    root = Path(data_root)
    pattern = str(root / "**" / "*.parquet")
    filters = ["trade_date IS NOT NULL", "adj_close > 0", "total_mv > 0"]
    parameters: list[object] = [pattern]
    if start_date is not None:
        filters.append("try_cast(trade_date AS DATE) >= CAST(? AS DATE)")
        parameters.append(start_date)
    if end_date is not None:
        filters.append("try_cast(trade_date AS DATE) <= CAST(? AS DATE)")
        parameters.append(end_date)
    parameters.append(constituent_count)
    query = f"""
        WITH raw AS (
            SELECT ts_code, trade_date, CAST(adj_close AS DOUBLE) AS adj_close,
                   CAST(total_mv AS DOUBLE) AS total_mv,
                   COALESCE(is_st, false) AS is_st,
                   COALESCE(is_suspended, false) AS is_suspended
            FROM (
                SELECT ts_code,
                       COALESCE(try_cast(trade_date AS DATE), try_strptime(trade_date, '%Y%m%d')) AS trade_date,
                       adj_close, total_mv, is_st, is_suspended
                FROM read_parquet(?, union_by_name=true)
            ) source
            WHERE {' AND '.join(filters)}
        ),
        dates AS (
            SELECT trade_date,
                   LEAD(trade_date) OVER (ORDER BY trade_date) AS next_trade_date
            FROM (SELECT DISTINCT trade_date FROM raw)
        ),
        prices AS (
            SELECT *,
                   LEAD(trade_date) OVER (PARTITION BY ts_code ORDER BY trade_date) AS next_stock_date,
                   LEAD(adj_close) OVER (PARTITION BY ts_code ORDER BY trade_date) AS next_adj_close
            FROM raw
        ),
        ranked AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY trade_date ORDER BY total_mv, ts_code) AS rank
            FROM prices
            WHERE NOT is_st AND NOT is_suspended
        ),
        selected AS (
            SELECT ranked.*, dates.next_trade_date
            FROM ranked
            JOIN dates USING (trade_date)
            WHERE rank <= ?
        )
        SELECT trade_date AS date,
               CASE WHEN COUNT(*) = COUNT(*) FILTER (
                   WHERE next_stock_date = next_trade_date AND next_adj_close > 0
               ) THEN AVG(next_adj_close / adj_close - 1) FILTER (
                   WHERE next_stock_date = next_trade_date AND next_adj_close > 0
               ) END AS return,
               COUNT(*) AS selected_count,
               COUNT(*) FILTER (
                   WHERE next_stock_date = next_trade_date AND next_adj_close > 0
               ) AS priced_count
        FROM selected
        GROUP BY trade_date
        HAVING MAX(next_trade_date) IS NOT NULL
        ORDER BY trade_date
    """
    connection = duckdb.connect()
    try:
        result = connection.execute(query, parameters).fetchdf()
        if not result.empty:
            result["date"] = pd.to_datetime(result["date"]).dt.date
        return result
    finally:
        connection.close()


def _calculate_returns(selected: pd.DataFrame, result: pd.DataFrame) -> pd.DataFrame:
    valid = selected.loc[selected["valid_next"]].copy()
    valid["daily_return"] = valid["next_adj_close"] / valid["adj_close"] - 1
    returns = valid.groupby("date")["daily_return"].mean().rename("return")
    result = result.merge(returns, left_on="date", right_index=True, how="left")
    result.loc[result["priced_count"].ne(result["selected_count"]), "return"] = float("nan")
    return result.sort_values("date").reset_index(drop=True)


def build_nav(returns: pd.DataFrame) -> pd.DataFrame:
    if returns["return"].isna().any():
        raise ValueError("missing selected holding prices: resolve valuation before building NAV")
    result = returns.copy()
    result["nav"] = (1 + result["return"].astype(float)).cumprod()
    return result


def build_underwater_periods(nav: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    peak_nav = None
    peak_date = None
    active: dict[str, object] | None = None
    for row in nav.itertuples(index=False):
        current_date = str(row.date)
        current_nav = float(row.nav)
        if peak_nav is None or current_nav >= peak_nav:
            if active is not None:
                rows.append(active)
                active = None
            peak_nav = current_nav
            peak_date = current_date
            continue
        drawdown = current_nav / peak_nav - 1
        if active is None:
            active = {
                "start_date": current_date,
                "end_date": current_date,
                "peak_date": peak_date,
                "trading_days": 1,
                "max_drawdown": drawdown,
            }
        else:
            active["end_date"] = current_date
            active["trading_days"] = int(active["trading_days"]) + 1
            active["max_drawdown"] = min(float(active["max_drawdown"]), drawdown)
    if active is not None:
        rows.append(active)
    return pd.DataFrame(rows, columns=["start_date", "end_date", "peak_date", "trading_days", "max_drawdown"])


def summarize_nav(nav: pd.DataFrame) -> dict[str, object]:
    episodes = build_underwater_periods(nav)
    if episodes.empty:
        return {"max_drawdown": 0.0, "longest_underwater_trading_days": 0, "underwater_episode_count": 0}
    longest = episodes.loc[episodes["trading_days"].idxmax()]
    return {
        "max_drawdown": float(episodes["max_drawdown"].min()),
        "longest_underwater_trading_days": int(longest["trading_days"]),
        "longest_underwater_start": longest["start_date"],
        "longest_underwater_end": longest["end_date"],
        "underwater_episode_count": int(len(episodes)),
    }
