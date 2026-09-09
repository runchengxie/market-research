type Episode = {peak_date: string; trough_date: string; recovery_date: string | null; observed_until: string;
  calendar_days: number; trading_sessions: number; censored: boolean; max_drawdown: number};
type Horizon = {years: number; mature_entries: number; immature_entries: number; loss_fraction: number | null;
  worst_return: number | null; median_return: number | null};
type Entry = {entry_date: string; breakeven_date: string | null; observed_until: string; calendar_days: number; trading_sessions: number; worst_return_before_breakeven: number; censored: boolean};
type RecoverySeries = {ts_code: string; name: string; group: string; role: string; start: string; end: string; observations: number;
  longest_completed_underwater_calendar_days: number | null; longest_observed_underwater_calendar_days: number;
  currently_underwater: boolean; current_underwater_calendar_days: number; gain_needed_to_recover: number;
  episodes: Episode[]; horizons: Horizon[]; entries: Entry[]};
export type Snapshot = {schema_version: number; series: RecoverySeries[]; issues: {group?: string; status: string}[];
  excluded: {ts_code: string; name: string; group: string; status: string}[]};
export function isRecoverySnapshot(value: unknown): value is Snapshot {
  const object = (item: unknown): item is Record<string, unknown> => item !== null && typeof item === 'object';
  const number = (item: unknown) => typeof item === 'number' && Number.isFinite(item);
  const nullableNumber = (item: unknown) => item === null || number(item);
  const text = (item: unknown) => typeof item === 'string' && item.length > 0;
  const records = (items: unknown, check: (row: Record<string, unknown>) => boolean) => Array.isArray(items) && items.every(item => object(item) && check(item));
  return object(value) && value.schema_version === 1
    && records(value.issues, row => text(row.status) && (row.group === undefined || text(row.group)))
    && records(value.excluded, row => ['ts_code', 'name', 'group', 'status'].every(key => text(row[key])))
    && records(value.series, row => ['ts_code', 'name', 'group', 'role', 'start', 'end'].every(key => text(row[key]))
      && ['observations', 'longest_observed_underwater_calendar_days', 'current_underwater_calendar_days', 'gain_needed_to_recover'].every(key => number(row[key]))
      && nullableNumber(row.longest_completed_underwater_calendar_days) && typeof row.currently_underwater === 'boolean'
      && records(row.episodes, item => ['peak_date', 'trough_date', 'observed_until'].every(key => text(item[key]))
        && (item.recovery_date === null || text(item.recovery_date)) && typeof item.censored === 'boolean'
        && ['calendar_days', 'trading_sessions', 'max_drawdown'].every(key => number(item[key])))
      && records(row.horizons, item => ['years', 'mature_entries', 'immature_entries'].every(key => number(item[key]))
        && ['loss_fraction', 'worst_return', 'median_return'].every(key => nullableNumber(item[key])))
      && records(row.entries, item => text(item.entry_date) && text(item.observed_until)
        && (item.breakeven_date === null || text(item.breakeven_date)) && number(item.calendar_days)
        && number(item.trading_sessions) && number(item.worst_return_before_breakeven) && typeof item.censored === 'boolean'));
}
