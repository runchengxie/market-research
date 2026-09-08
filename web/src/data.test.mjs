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
});

test("does not publish the retired animal index dataset", () => {
  assert.equal(fs.existsSync(path.join(root, "animal")), false);
  assert.equal(fs.existsSync(path.join(root, "plant")), false);
});
