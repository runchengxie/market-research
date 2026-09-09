"""Derived recovery notebook outputs; never publish input paths or raw prices."""
from html import escape
from pathlib import Path

import pandas as pd

from .recovery import EPISODE_COLUMNS, analyze_recovery


def write_recovery_report(nav: pd.DataFrame, output: Path, names: dict[str, str], issues=()) -> None:
    summaries, episodes, entries, horizons = [], [], [], []
    for code, series in nav.groupby("ts_code"):
        result = analyze_recovery(series)
        summaries.append({"ts_code": code, "name": names.get(code, code), **result["summary"]})
        for key, collection in [("episodes", episodes), ("entries", entries), ("horizons", horizons)]:
            collection.extend({"ts_code": code, **row} for row in result[key].to_dict("records"))
    summary = pd.DataFrame(summaries, columns=["ts_code", "name", "start", "end", "observations",
        "completed_episode_count", "longest_completed_underwater_calendar_days",
        "longest_observed_underwater_calendar_days", "currently_underwater",
        "current_underwater_calendar_days", "current_peak_date", "gain_needed_to_recover",
        "unrecovered_entry_count", "historical_only"])
    episode_frame = pd.DataFrame(episodes, columns=["ts_code", *EPISODE_COLUMNS])
    entry_frame = pd.DataFrame(entries, columns=["ts_code", "entry_date", "breakeven_date", "observed_until",
        "calendar_days", "trading_sessions", "censored", "worst_return_before_breakeven"])
    horizon_frame = pd.DataFrame(horizons, columns=["ts_code", "years", "mature_entries", "immature_entries",
        "loss_fraction", "worst_return", "median_return"])
    for name, frame in [("summary", summary), ("episodes", episode_frame), ("entries", entry_frame), ("horizons", horizon_frame)]:
        frame.to_csv(output / f"recovery_{name}.csv", index=False)

    def table(frame):
        return frame.to_html(index=False, escape=True, na_rep="N/A")

    columns = {"name": "指数", "start": "样本起点", "end": "样本末日",
        "longest_completed_underwater_calendar_days": "最长已完成水下期（自然日）",
        "longest_observed_underwater_calendar_days": "最长已观察水下期（自然日）",
        "currently_underwater": "当前仍在水下", "current_underwater_calendar_days": "当前已等待（自然日）",
        "gain_needed_to_recover": "当前回本所需涨幅"}
    display = summary[list(columns)].rename(columns=columns).copy()
    display["当前回本所需涨幅"] = display["当前回本所需涨幅"].map(lambda x: f"{x:.2%}")
    history = horizon_frame.copy()
    history["ts_code"] = history.ts_code.map(lambda code: names.get(code, code))
    for column in ("loss_fraction", "worst_return", "median_return"):
        history[column] = history[column].map(lambda x: "N/A" if pd.isna(x) else f"{x:.2%}")
    history = history.rename(columns={"ts_code": "指数", "years": "持有年数", "mature_entries": "期限已满样本",
        "immature_entries": "期限未满样本", "loss_fraction": "历史亏损比例", "worst_return": "最差收益", "median_return": "中位收益"})
    longest = episode_frame.sort_values("calendar_days", ascending=False).head(15)
    bars = []
    scale = max(longest.calendar_days.max(), 1) if len(longest) else 1
    for row in longest.itertuples():
        state = "仍未恢复，至少" if row.censored else "已恢复"
        label = f"{names.get(row.ts_code, row.ts_code)} {row.peak_date} → {row.recovery_date or row.observed_until} · {state}{row.calendar_days}天"
        color = "#b05236" if row.censored else "#227c79"
        bars.append(f'<div class="episode"><span>{escape(label)}</span><div style="background:{color};width:{max(1, 100 * row.calendar_days / scale):.2f}%;height:12px"></div></div>')
    worst_entries = entry_frame.sort_values("calendar_days", ascending=False).head(20).copy()
    worst_entries["ts_code"] = worst_entries.ts_code.map(lambda code: names.get(code, code))
    html = '''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quant Market Research · 回本等待研究</title><style>body{font:16px system-ui;max-width:1200px;margin:36px auto;padding:0 16px;color:#183c52}table{border-collapse:collapse;font-size:13px;width:100%}td,th{border:1px solid #ddd;padding:8px}section{overflow-x:auto;margin:24px 0}.episode{margin:14px 0;font-size:13px}.warning{background:#fff0da;padding:18px;line-height:1.7}h2{margin-top:36px}</style>
<h1>如果买在不幸的时点，要等多久回本？</h1>
<p><a href="../">返回研究首页</a> · 现金流与微盘指数研究 · 非交易策略</p>
<div class="warning">这是历史观察，不存在由这些数字保证的未来最长回本期限。现金流按价格指数（不含分红）和供应商税前全收益指数分别展示，全收益名称有明确后缀，不代表本地复制了分红账本；微盘使用供应商点位，分红口径尚未独立核验。不计税费、通胀或机会成本。部分指数历史为回溯构建，不等于实时运行记录。</div>
<p>水下期按前期高点到首次恢复至该高点计算；未恢复的记录只代表“截至样本末至少等待这么久”（右删失），不会剔除或当作已经回本。只观察样本开始以后的高点，早于样本起点的套牢经历无法识别。</p>
<h2>历史最长与当前等待</h2>'''
    html += "<section>" + table(display) + "</section><h2>最长水下阶段</h2>" + "".join(bars)
    html += "<h2>持有固定年限：亏损比例与最差结果</h2><p>在买入日的1/3/5/10周年或之后的首个交易日评价。期限未满单列，不算盈利；重叠窗口不是独立样本，比例不是未来概率。</p><section>" + table(history) + "</section>"
    html += "<h2>等待最久的历史买入日（包括尚未回本）</h2><p>breakeven_date为空且censored=True表示未恢复；calendar_days为已观察下界。第一回本触点不等于此后一直盈利；短暂回本后再次下跌不计入首次等待期。最后一天买入尚无后续观测，也属于删失。</p><section>" + table(worst_entries) + "</section>"
    html += "<p>自制400股净值因已选持仓缺报价问题尚未通过审计，不纳入这次回本比较；未提供的Wind日线也不以年度数据拼接替代。</p></html>"
    if issues:
        html = html.replace("</html>", "<h2>数据校验阻断</h2>" + table(pd.DataFrame(issues)) + "</html>")
    (output / "recovery.html").write_text(html, encoding="utf-8")
