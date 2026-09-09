import { useEffect, useRef } from "react";
import { echarts, type EChartsOption } from "./echarts";

type ChartRow = Record<string, string>;

function Chart({ option }: { option: EChartsOption }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption(option);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);
  return <div ref={ref} className="research-chart" role="img" />;
}

const axis = { axisLine: { lineStyle: { color: "#d8d0c3" } }, axisLabel: { color: "#81796e" } };
const grid = { left: 54, right: 24, top: 28, bottom: 48 };

export function NavChart({ rows, name, color }: { rows: ChartRow[]; name: string; color: string }) {
  return <Chart option={{ tooltip: { trigger: "axis" }, dataZoom: [{ type: "inside" }, { type: "slider", height: 12, bottom: 8, showDetail: false }], grid, xAxis: { ...axis, type: "category", data: rows.map((row) => row.date), axisLabel: { ...axis.axisLabel, formatter: (value: string) => value.slice(0, 4), hideOverlap: true } }, yAxis: { ...axis, type: "value", scale: true }, series: [{ name, type: "line", showSymbol: false, smooth: true, data: rows.map((row) => Number(row.nav)), lineStyle: { width: 2.5, color }, areaStyle: { color: `${color}18` } }] }} />;
}

export function AnnualChart({ rows }: { rows: ChartRow[] }) {
  return <Chart option={{ tooltip: { trigger: "axis", formatter: (params: any) => { const item = Array.isArray(params) ? params[0] : params; return `${item.axisValue}<br/>年度收益：${(Number(rows[item.dataIndex].return) * 100).toFixed(2)}%`; } }, grid, xAxis: { ...axis, type: "category", data: rows.map((row) => row.year), axisLabel: { ...axis.axisLabel, interval: 2 } }, yAxis: { ...axis, type: "value", axisLabel: { ...axis.axisLabel, formatter: "{value}%" } }, series: [{ type: "bar", data: rows.map((row) => ({ value: Number(row.return) * 100, itemStyle: { color: Number(row.return) >= 0 ? "#1267d6" : "#8e4d48" } })) }] }} />;
}

export function MetricChart({ rows, value, label }: { rows: ChartRow[]; value: string; label: string }) {
  const ordered = [...rows].sort((left, right) => Number(left.window_years) - Number(right.window_years));
  return <Chart option={{ tooltip: { trigger: "axis", formatter: (params: any) => { const item = Array.isArray(params) ? params[0] : params; const row = ordered[item.dataIndex]; return `${row.window_years}年<br/>${label}：${(Number(row[value]) * 100).toFixed(1)}%`; } }, grid: { ...grid, bottom: 58 }, xAxis: { ...axis, type: "category", data: ordered.map((row) => `${row.window_years}年`), axisLabel: { ...axis.axisLabel, interval: 0 } }, yAxis: { ...axis, type: "value", axisLabel: { ...axis.axisLabel, formatter: "{value}%" } }, series: [{ type: "bar", data: ordered.map((row) => Number(row[value]) * 100), itemStyle: { color: value === "max_drawdown" ? "#8e4d48" : "#1267d6" } }] }} />;
}

export function UnderwaterChart({ rows }: { rows: ChartRow[] }) {
  const top = [...rows].sort((left, right) => Number(right.trading_days) - Number(left.trading_days)).slice(0, 10);
  const display = [...top].reverse();
  return <Chart option={{ tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: (params: any) => { const item = Array.isArray(params) ? params[0] : params; const row = display[item.dataIndex]; return `${row.start_date} 至 ${row.end_date}<br/>未回到前高的交易日数：${row.trading_days}<br/>最大回撤：${(Number(row.max_drawdown) * 100).toFixed(1)}%`; } }, grid: { left: 112, right: 28, top: 16, bottom: 30 }, xAxis: { ...axis, type: "value", name: "交易日", nameTextStyle: { color: "#81796e" } }, yAxis: { ...axis, type: "category", data: display.map((row) => row.start_date), axisLabel: { ...axis.axisLabel, width: 90 } }, series: [{ type: "bar", data: display.map((row) => Number(row.trading_days)), itemStyle: { color: "#b96800" } }] }} />;
}
