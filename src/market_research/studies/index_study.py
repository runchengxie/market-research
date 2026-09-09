"""Read-only, shared-asset index evidence notebook; no strategy selection."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


CATALOG = [
    ("932368.CSI", "800现金流", "cashflow_price", "baseline"),
    ("980092.SZ", "国证自由现金流", "cashflow_price", "baseline"),
    ("931082.CSI", "A500现金流", "cashflow_price", "extension"),
    ("932369.CSI", "1000现金流", "cashflow_price", "extension"),
    ("932365.CSI", "全指现金流", "cashflow_price", "control"),
    ("932367.CSI", "500现金流", "cashflow_price", "control"),
    ("883418.TI", "同花顺微盘", "microcap_vendor_close", "benchmark"),
    ("932000.CSI", "中证2000", "microcap_vendor_close", "smallcap_control"),
    ("399303.SZ", "国证2000", "microcap_vendor_close", "smallcap_control"),
    ("8841431.WI", "万得微盘", "microcap_vendor_close", "reference_only"),
]


def run_study(study_path: Path) -> Path:
    config = json.loads(study_path.read_text())
    start, end = pd.Timestamp(config["start"]), pd.Timestamp(config["end"])
    if start >= end:
        raise ValueError("start must precede end")
    output = Path(config["output_root"]).expanduser().resolve()
    repo = Path(__file__).resolve().parents[3]
    if output.is_relative_to(repo):
        raise ValueError("research output must be outside the code repository")
    frames, provenance = [], []
    for source in config["sources"]:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        frame = pd.read_parquet(path, columns=["ts_code", "trade_date", "close"])
        frames.append(frame)
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        provenance.append({"path": str(path), "sha256": digest, "rows": len(frame)})
    raw = pd.concat(frames, ignore_index=True)
    raw["date"] = pd.to_datetime(raw.trade_date.astype(str), format="mixed", errors="raise")
    raw["close"] = pd.to_numeric(raw.close, errors="raise")
    if raw.groupby(["ts_code", "date"]).close.nunique(dropna=False).gt(1).any():
        raise ValueError("conflicting duplicate index prices; resolve input versions")
    raw = raw.drop_duplicates(["ts_code", "date"])
    raw = raw.loc[raw.date.between(start, end)]
    coverage, comparisons, paths, issues = [], [], [], []
    for code, name, group, role in CATALOG:
        series = raw.loc[raw.ts_code.eq(code)].sort_values("date")
        invalid = series.close.isna() | series.close.le(0) | series.close.isin([float("inf"), -float("inf")])
        status = "invalid" if invalid.any() else "available" if len(series) >= 2 else "missing"
        coverage.append({"ts_code": code, "name": name, "group": group, "role": role,
                         "status": status, "rows": len(series),
                         "start": str(series.date.min().date()) if len(series) else None,
                         "end": str(series.date.max().date()) if len(series) else None})
    coverage_frame = pd.DataFrame(coverage)
    for group, members in coverage_frame.loc[coverage_frame.status.eq("available")].groupby("group"):
        panel = raw.loc[raw.ts_code.isin(members.ts_code)].pivot(index="date", columns="ts_code", values="close").sort_index()
        lower = max(panel[c].first_valid_index() for c in panel)
        upper = min(panel[c].last_valid_index() for c in panel)
        panel = panel.loc[lower:upper]
        if len(panel) < 2 or panel.isna().any().any():
            issues.append({"group": group, "status": "blocked_calendar_or_price_gap"})
            continue
        for code in panel:
            values = panel[code]
            nav = values / values.iloc[0]
            days = (values.index[-1] - values.index[0]).days
            comparisons.append({"ts_code": code, "group": group, "start": str(lower.date()),
                                "end": str(upper.date()), "observations": len(values),
                                "total_return": float(nav.iloc[-1] - 1),
                                "cagr": float(nav.iloc[-1] ** (365.25 / days) - 1),
                                "max_drawdown": float((nav / nav.cummax() - 1).min())})
            paths.append(pd.DataFrame({"date": nav.index, "ts_code": code, "nav": nav.values}))
    output.mkdir(parents=True, exist_ok=True)
    comparison = pd.DataFrame(comparisons)
    coverage_frame.to_csv(output / "coverage.csv", index=False)
    comparison.to_csv(output / "comparison.csv", index=False)
    if paths:
        pd.concat(paths).to_csv(output / "normalized_nav.csv", index=False)
    (output / "receipt.json").write_text(json.dumps({
        "study": "cashflow_microcap_index_evidence_v1", "research_only": True,
        "replication_verified": False, "requested_start": config["start"], "requested_end": config["end"],
        "inputs": provenance, "issues": issues,
        "limitations": ["Index closes, not executable strategy returns", "No historical constituent completeness claim",
                        "Microcap vendor dividend conventions not independently verified", "Historical index series may include backcasts"],
    }, ensure_ascii=False, indent=2) + "\n")
    html = """<!doctype html><html lang="zh"><meta charset="utf-8"><title>Quant Market Research · 指数研究</title>
<style>body{max-width:1100px;margin:40px auto;font:16px system-ui}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px;border:1px solid #ddd}h1,h2{color:#183c52}</style>
<h1>现金流与微盘：可重跑研究笔记</h1>
<p>研究用途。以下是供应商指数点位的描述性比较，不是选股策略、指数复刻或可交易收益。
现金流只比较价格指数；微盘供应商的分红口径尚未独立核验。每组使用共同起止日，内部缺报价则阻断比较，不前填。</p>
<h2>数据覆盖</h2>""" + coverage_frame.to_html(index=False, escape=True) + "<h2>同区间表现</h2>" + comparison.to_html(index=False, escape=True)
    html += "<p>缺失数据不以其他指数替代；自制400股需先通过缺报价与历史资格审计。400股指数收益不能证明每周3股策略有效。</p></html>"
    (output / "report.html").write_text(html, encoding="utf-8")
    return output
