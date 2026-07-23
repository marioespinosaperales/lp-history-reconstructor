# Evidence dashboard — LP PnL by range width

Reads the DuckDB marts snapshot at `sources/lp/lp_marts.duckdb`
(regenerated with `make snapshot` from the repo root).

## Local

```bash
# from repo root
make transform && make snapshot
cd dashboard
npm install
npm run sources
npm run dev
```

## Deploy on Vercel

Already live: https://lp-history-reconstructor.vercel.app/

Repo-root `vercel.json` builds the `dashboard/` Evidence app (install → sources → build).
GitHub is connected, so pushes that change the dashboard can redeploy automatically.

If the site asks for a login, disable **Deployment Protection**
(Vercel project → Settings → Deployment Protection).

Refresh data by re-running `make snapshot`, committing `sources/lp/lp_marts.duckdb`, and pushing
(or add a deploy hook later for scheduled refreshes).
