import test from "node:test";
import assert from "node:assert/strict";
import { formatPercent, summarizeNav } from "./dashboard.mjs";

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
