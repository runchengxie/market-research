import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

test("published research snapshots exclude local paths and credential assignments", () => {
  const root = fileURLToPath(new URL("../public", import.meta.url));
  const violations = [];
  function visit(path) {
    for (const entry of readdirSync(path, { withFileTypes: true })) {
      const full = join(path, entry.name);
      if (entry.isDirectory()) visit(full);
      else if (/\.(json|csv|html|md)$/.test(entry.name)) {
        if (/\/home\/|\/Users\/|\/mnt\/|TUSHARE_TOKEN=|API_KEY=|SECRET_KEY=/.test(readFileSync(full, "utf8"))) violations.push(full);
      }
    }
  }
  visit(root);
  assert.deepEqual(violations, []);
});
