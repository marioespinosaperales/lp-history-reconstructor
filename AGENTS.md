# lp-history-reconstructor — Project conventions

Reconstruct Uniswap V2/V3 LP history from on-chain events (event sourcing),
attribute V3 positions to wallets via NPM, and verify against live contract state.

## Architecture

- `src/lp_history/rpc/` — JSON-RPC client (Alchemy): getLogs, blockNumber, eth_call
- `src/lp_history/index/` — V2 + V3 + NPM ABI decode, chunked backfill
- `src/lp_history/state/` — V2 Sync fold, V3 position fold (range width), NPM tokenId→wallet
- `src/lp_history/verify/` — getReserves() / liquidity()+slot0() / positions(tokenId)
- `config/` — pools + npm + pipeline params; secrets ONLY via `LP_` env vars

## Rules

- Python 3.12, type hints on public signatures, functions over classes.
- New config → YAML in `config/` + pydantic model in `settings.py`. Never hardcode.
- Data and logs are NEVER committed.
- Tests use fixtures of real RPC/log payloads; mock HTTP with respx.
- English only in all committed text.

## Commands

- `make backfill` — index configured window, fold state, verify
- `make lint && make test` — required before every commit
