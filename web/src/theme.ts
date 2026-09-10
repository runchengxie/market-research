export type ThemeChoice = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "market-research-theme";

export function resolveTheme(choice: ThemeChoice, prefersDark: boolean): ResolvedTheme {
  return choice === "system" ? (prefersDark ? "dark" : "light") : choice;
}

export function readThemeChoice(storage?: Pick<Storage, "getItem"> | null): ThemeChoice {
  const value = storage?.getItem(THEME_STORAGE_KEY);
  return value === "light" || value === "dark" || value === "system" ? value : "system";
}

export function persistThemeChoice(storage: Pick<Storage, "setItem">, choice: ThemeChoice): void {
  storage.setItem(THEME_STORAGE_KEY, choice);
}

export function applyTheme(choice: ThemeChoice, prefersDark: boolean, documentElement: Pick<HTMLElement, "setAttribute"> & { dataset: DOMStringMap }): ResolvedTheme {
  const resolved = resolveTheme(choice, prefersDark);
  documentElement.dataset.theme = resolved;
  documentElement.setAttribute("data-theme", resolved);
  return resolved;
}

export type ChartTheme = { axis: string; grid: string; label: string; tooltip: string };
const fallbackChartTheme: ChartTheme = { axis: "#d8d0c3", grid: "#e8e1d6", label: "#514b43", tooltip: "#252525" };

export function readChartTheme(): ChartTheme {
  if (typeof document === "undefined" || typeof getComputedStyle === "undefined") return fallbackChartTheme;
  const styles = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback;
  return { axis: read("--chart-axis", fallbackChartTheme.axis), grid: read("--chart-grid", fallbackChartTheme.grid), label: read("--chart-label", fallbackChartTheme.label), tooltip: read("--chart-tooltip", fallbackChartTheme.tooltip) };
}
