export function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

export function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"' && text[index + 1] === '"' && quoted) { cell += '"'; index += 1; continue; }
    if (char === '"') { quoted = !quoted; continue; }
    if (char === "," && !quoted) { row.push(cell); cell = ""; continue; }
    if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
      row.push(cell); cell = "";
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      continue;
    }
    cell += char;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const headers = rows.shift() ?? [];
  return rows.map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])));
}

export function summarizeNav(rows) {
  const clean = rows
    .map((row) => ({ date: row.date, nav: Number(row.nav) }))
    .filter((row) => row.date && Number.isFinite(row.nav));
  if (!clean.length) return { start: null, end: null, return: null, drawdown: null };
  let peak = clean[0].nav;
  let drawdown = 0;
  for (const row of clean) {
    peak = Math.max(peak, row.nav);
    drawdown = Math.min(drawdown, row.nav / peak - 1);
  }
  return {
    start: clean[0].date,
    end: clean.at(-1).date,
    return: clean.at(-1).nav / clean[0].nav - 1,
    drawdown,
  };
}

export function filterByRange(rows, range) {
  if (range === "all") return rows;
  const start = range === "ytd" ? `${new Date().getFullYear()}-01-01` : `${Number(range) - 1}-01-01`;
  return rows.filter((row) => row.date >= start);
}

export function sortRows(rows, key, direction = "asc") {
  return [...rows].sort((left, right) => {
    const leftNumber = Number(left[key]);
    const rightNumber = Number(right[key]);
    const comparison = Number.isFinite(leftNumber) && Number.isFinite(rightNumber)
      ? leftNumber - rightNumber
      : String(left[key] ?? "").localeCompare(String(right[key] ?? ""));
    return direction === "desc" ? -comparison : comparison;
  });
}
