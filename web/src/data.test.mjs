import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../public/data");

test("publishes the migrated cross-market liquidity snapshot", () => {
  const summary = JSON.parse(fs.readFileSync(path.join(root, "liquidity/summary.json"), "utf8"));
  assert.deepEqual(summary.markets.map((market) => market.market), ["US", "HK", "A-share"]);
  assert.equal(summary.method.roll_days, 20);
  assert.ok(summary.markets.every((market) => market.buckets.length >= 4));
  assert.deepEqual(summary.periods.map((period) => period.period), ["2020-2024", "2025", "2026 YTD"]);
  assert.ok(summary.periods.every((period) => ["verified", "incomplete"].includes(period.status)));
});

test("publishes the Barra market-evidence snapshot", () => {
  const summary = JSON.parse(fs.readFileSync(path.join(root, "barra/barra_summary.json"), "utf8"));
  const quantiles = fs.readFileSync(path.join(root, "barra/barra_size_quantiles.csv"), "utf8");
  assert.equal(summary.legacy_barra_result.factor_count, 19);
  assert.equal(summary.size_monotonicity.quantiles, 10);
  assert.match(quantiles, /formation_date,bucket,mean_forward_return/);
});

test("publishes the historical Barra report datasets", () => {
  const factors = JSON.parse(fs.readFileSync(path.join(root, "barra/historical_factor_summary.json"), "utf8"));
  const yearly = fs.readFileSync(path.join(root, "barra/factor_yearly.csv"), "utf8");
  const correlations = JSON.parse(fs.readFileSync(path.join(root, "barra/factor_correlation.json"), "utf8"));
  assert.equal(factors.length, 19);
  assert.match(yearly, /year,factor,days,period_start/);
  assert.ok(correlations.size);
});

test("does not publish the retired animal index dataset", () => {
  assert.equal(fs.existsSync(path.join(root, "animal")), false);
  assert.equal(fs.existsSync(path.join(root, "plant")), false);
});
