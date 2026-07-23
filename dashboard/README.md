# Evidence dashboard for LP range-width PnL.

## Local

```bash
# from repo root, after make transform && make snapshot
cd dashboard
npm install
npm run sources
npm run dev
```

The DuckDB snapshot lives at `sources/lp/lp_marts.duckdb` (generated, not hand-edited).
