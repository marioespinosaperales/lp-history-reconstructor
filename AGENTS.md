# lp-history-reconstructor — Project conventions

Reconstruct Uniswap V2/V3 LP history from on-chain events (event sourcing),
attribute V3 positions to wallets via NPM, verify against live contract state,
and publish fees / IL vs HODL marts (by range width) via DuckDB + dbt.

## Architecture

- `src/lp_history/rpc/` — JSON-RPC client (Alchemy): getLogs, blockNumber, eth_call
- `src/lp_history/index/` — V2 + V3 + NPM ABI decode, chunked backfill
- `src/lp_history/state/` — V2 Sync fold, V3 position fold (range width), NPM tokenId→wallet
- `src/lp_history/verify/` — getReserves() / liquidity()+slot0() / positions(tokenId)
- `src/lp_history/analytics/` — price helpers + NFT snapshot enrichment for dbt
- `src/lp_history/load/` — Parquet Hive store + DuckDB raw loader
- `dbt/` — staging / intermediate / marts (business metrics)
- `dashboard/` — Evidence over exported marts snapshot
- `config/` — pools + npm + pipeline params; secrets ONLY via `LP_` env vars

## Rules

- Python 3.12, type hints on public signatures, functions over classes.
- New config → YAML in `config/` + pydantic model in `settings.py`. Never hardcode.
- Data and logs are NEVER committed (except `dashboard/sources/lp/lp_marts.duckdb`).
- Business metrics live in dbt, not in Python folds.
- Tests use fixtures of real RPC/log payloads; mock HTTP with respx.
- English only in all committed text.

## Commands

- `make backfill` — index configured window, fold state, verify
- `make transform` — NFT snapshot + DuckDB load + `dbt build`
- `make snapshot` — export marts for Evidence
- `make lint && make test` — required before every commit
