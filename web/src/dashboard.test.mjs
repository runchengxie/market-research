import test from "node:test";
import assert from "node:assert/strict";
import { filterByRange, formatPercent, parseCsv, sortRows, summarizeNav } from "./dashboard.mjs";

test("formats decimal returns as percentages", () => {
  assert.equal(formatPercent(0.1234), "12.3%");
  assert.equal(formatPercent(-0.05), "-5.0%");
});

test("summarizes a navigation series without hiding missing values", () => {
  const result = summarizeNav([
    { date: "2024-01-01", nav: "100" },
    { date: "2024-01-02", nav: "110" },
    { date: "2024-01-03", nav: "99" },
  ]);
  assert.equal(result.start, "2024-01-01");
  assert.equal(result.end, "2024-01-03");
  assert.ok(Math.abs(result.return - -0.01) < 1e-12);
  assert.ok(Math.abs(result.drawdown - -0.1) < 1e-12);
});

test("parses quoted CSV rows into reusable records", () => {
  assert.deepEqual(parseCsv('name,return\n"自由现金流,指数",0.12\n'), [{ name: "自由现金流,指数", return: "0.12" }]);
});

test("filters dated rows and sorts numeric metrics for interactive tables", () => {
  const rows = [{ date: "2020-01-01", score: "2" }, { date: "2024-01-01", score: "10" }, { date: "2025-01-01", score: "3" }];
  assert.deepEqual(filterByRange(rows, "2024"), rows.slice(1));
  assert.deepEqual(sortRows(rows, "score", "desc"), [rows[1], rows[2], rows[0]]);
});
