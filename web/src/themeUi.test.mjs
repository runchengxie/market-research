import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const [html, main, styles, charts] = await Promise.all([
  readFile(new URL("../index.html", import.meta.url), "utf8"),
  readFile(new URL("./main.tsx", import.meta.url), "utf8"),
  readFile(new URL("./styles.css", import.meta.url), "utf8"),
  readFile(new URL("./components/ResearchCharts.tsx", import.meta.url), "utf8"),
]);

test("theme is applied before the page paints and can be changed from the shell", () => {
  assert.match(html, /market-research-theme/);
  assert.match(html, /document\.documentElement\.dataset\.theme/);
  assert.match(main, /className="theme-toggle"/);
  assert.match(main, /persistThemeChoice/);
});

test("dark mode defines semantic palette tokens", () => {
  assert.match(styles, /\[data-theme="dark"\]/);
  assert.match(styles, /--paper:/);
  assert.match(styles, /--chart-grid:/);
  assert.match(styles, /--table-hover:/);
});

test("charts read their axis palette from the active theme", () => {
  assert.match(charts, /readChartTheme/);
  assert.match(charts, /theme\.grid/);
});
