# lp-history-reconstructor — Project conventions

Reconstruct Uniswap V2 pool history from on-chain events (event sourcing),
verify reconstructed reserves against `getReserves()`.

## Architecture

- `src/lp_history/rpc/` — JSON-RPC client (Alchemy): getLogs, blockNumber, eth_call
- `src/lp_history/index/` — decode V2 Swap/Mint/Burn/Sync, chunked backfill
- `src/lp_history/load/` — Hive-partitioned Parquet event store + checkpoints
- `src/lp_history/state/` — fold Sync events into reconstructed reserves
- `src/lp_history/verify/` — compare reconstructed vs on-chain getReserves()
- `config/` — pools + pipeline params; secrets ONLY via `LP_` env vars

## Rules

- Python 3.12, type hints on public signatures, functions over classes.
- New config → YAML in `config/` + pydantic model in `settings.py`. Never hardcode.
- Data and logs are NEVER committed.
- Tests use fixtures of real RPC/log payloads; mock HTTP with respx.
- English only in all committed text.

## Commands

- `make backfill` — index configured window, fold state, verify
- `make lint && make test` — required before every commit
