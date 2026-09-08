export function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
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
