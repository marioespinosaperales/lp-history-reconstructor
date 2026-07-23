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

## Deploy on Vercel (same pattern as crypto-market-elt)

1. Import the GitHub repo in Vercel.
2. Set **Root Directory** to `dashboard`.
3. Framework: Other. Build settings come from `vercel.json`:
   - Install: `npm install`
   - Build: `npm run sources && npm run build`
   - Output: `build`
4. Deploy. If the site asks for a login, disable **Deployment Protection**
   (Vercel project → Settings → Deployment Protection) so the CV link is public.

Refresh later by re-running `make snapshot`, committing `sources/lp/lp_marts.duckdb`, and pushing
(or add a deploy hook like Project 1 when you want scheduled refreshes).
