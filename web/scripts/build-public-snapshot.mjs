import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const output = path.join(root, "outputs");
const target = path.resolve(here, "../public/data");
fs.mkdirSync(target, { recursive: true });

const parseCsv = (text) => {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines.shift().split(",");
  return lines.filter(Boolean).map((line) => {
    const values = line.split(",");
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
};

const summary = JSON.parse(fs.readFileSync(path.join(output, "microcap_summary.json"), "utf8"));
const nav = parseCsv(fs.readFileSync(path.join(output, "microcap_nav.csv"), "utf8"))
  .map((row) => ({ date: row.date, nav: Number(row.nav), daily_return: Number(row.daily_return), constituents: Number(row.constituents) }))
  .filter((row) => row.date && Number.isFinite(row.nav));

const manifest = {
  generated_at: new Date().toISOString(),
  sources: ["market-research A-share rule reconstruction"],
  markets: { a_share: "published", hk: "pending local refresh", us: "pending local refresh", jp: "pending local refresh" },
  privacy: "Derived snapshot only; raw market data and local paths are excluded.",
};
for (const [name, value] of Object.entries({ microcap_summary: summary, microcap_nav: nav, manifest })) {
  fs.writeFileSync(path.join(target, `${name}.json`), `${JSON.stringify(value, null, 2)}\n`);
}
