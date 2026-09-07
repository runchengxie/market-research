# Compatibility and migration notes

The new project is a research entry point, not a destructive replacement for
the source projects.

## Existing projects

- `index-research` remains the reference for the existing public microcap
  snapshots, index research page, and historical output files.
- `market-liquidity-profiles` remains the reference for the original capacity
  adapters, capacity schema, and cross-market liquidity result notes.
- `nira` remains the source of JPX/J-Quants data and its own Japan-specific
  research workflows.

The new implementations are tested against small deterministic fixtures. A
full historical parity comparison is required before replacing an old command.

## Known intentional differences

1. The canonical panel preserves native currency; the old capacity project
   often normalized snapshot outputs to USD immediately.
2. The JP adapter currently lacks a paired market-cap source because the nira
   daily bars expose price, volume, and traded value but not total market cap.
   JP market-cap-dependent reports therefore remain `incomplete`.
3. The new microcap reconstruction exposes selected/priced counts and can join
   lagged liquidity diagnostics; its return rule remains the smallest-400,
   equal-weight, next-market-day research rule.
4. The new report bundle is static JSON/CSV in the first phase; the existing
   `index-research` frontend is not migrated yet.
