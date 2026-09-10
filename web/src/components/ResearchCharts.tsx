import { useEffect, useRef } from "react";
import { echarts, type EChartsOption } from "./echarts";
import { readChartTheme } from "../theme";

type ChartRow = Record<string, string>;
type Series = { name: string; values: number[]; color: string };

function Chart({ option }: { option: EChartsOption }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption(option, true);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);
  return <div ref={ref} className="research-chart" role="img" />;
}

const grid = { left: 72, right: 72, top: 24, bottom: 48 };

export function ResearchBarChart({ rows, labelKey, valueKey, color = "#1267d6", formatter = (value: number) => `${(value * 100).toFixed(1)}%`, logScale = false }: { rows: ChartRow[]; labelKey: string; valueKey: string; color?: string; formatter?: (value: number) => string; logScale?: boolean }) {
  const theme = readChartTheme();
  const axis = { axisLine: { lineStyle: { color: theme.axis } }, axisLabel: { color: theme.axis } };
  const values = rows.map((row) => { const raw = row[valueKey]; if (raw == null || raw.trim() === '') return null; const value = Number(raw); return Number.isFinite(value) ? value : null; });
  const finiteValues = values.filter((value): value is number => value != null);
  const canUseLog = logScale && finiteValues.length > 0 && finiteValues.every((value) => value > 0);
  const formatValue = (value: unknown) => value == null || value === "" || !Number.isFinite(Number(value)) ? "未提供" : formatter(Number(value));
  return <Chart option={{ animationDuration: 220, grid, tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: formatValue }, xAxis: { ...axis, type: canUseLog ? "log" : "value", axisLabel: { ...axis.axisLabel, hideOverlap: true, formatter: (value: number) => canUseLog ? String(value) : formatter(value) }, splitLine: { lineStyle: { color: theme.grid } } }, yAxis: { ...axis, type: "category", data: rows.map((row) => row[labelKey]), axisLabel: { ...axis.axisLabel, width: 150, overflow: "truncate" } }, series: [{ type: "bar", data: values, barMaxWidth: 18, label: { show: true, position: "right", color: theme.label, fontSize: 10, formatter: (params: any) => formatValue(params.value) }, itemStyle: { color: (params: any) => Number(params.value) < 0 ? "#8e4d48" : color }, markLine: canUseLog ? undefined : { silent: true, symbol: "none", lineStyle: { color: theme.axis, width: 1 }, data: [{ xAxis: 0 }] } }] }} />;
}

export function ResearchLineChart({ series, labels }: { series: Series[]; labels: string[] }) {
  const theme = readChartTheme();
  const axis = { axisLine: { lineStyle: { color: theme.axis } }, axisLabel: { color: theme.axis } };
  return <Chart option={{ animationDuration: 220, tooltip: { trigger: "axis" }, dataZoom: [{ type: "inside" }, { type: "slider", height: 12, bottom: 8, showDetail: false }], grid, xAxis: { ...axis, type: "category", data: labels, axisLabel: { ...axis.axisLabel, hideOverlap: true, formatter: (value: string) => value.length > 7 ? value.slice(0, 7) : value } }, yAxis: { ...axis, type: "value", scale: true, splitLine: { lineStyle: { color: theme.grid } } }, series: series.map((item) => ({ name: item.name, type: "line", showSymbol: false, smooth: true, data: item.values, lineStyle: { width: 2.5, color: item.color }, areaStyle: series.length === 1 ? { color: `${item.color}18` } : undefined })) }} />;
}
