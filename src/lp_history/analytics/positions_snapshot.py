"""Write pool-matched NFT positions (wallet + range width) for dbt joins.

NPM events alone do not carry tickLower/tickUpper; those come from
``positions(tokenId)``. Missing Transfer history is filled via ``ownerOf``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from eth_utils import to_checksum_address

from lp_history.analytics.price import is_full_range, range_bucket, range_width_pct
from lp_history.index.npm_abi import (
    decode_owner_of,
    decode_positions,
    owner_of_calldata,
    positions_calldata,
)
from lp_history.rpc.client import RpcClient
from lp_history.settings import PoolConfig
from lp_history.state.npm_wallets import load_npm_events, wallet_by_token_id

logger = logging.getLogger(__name__)

SNAPSHOT_COLUMNS = [
    "pool_name",
    "pool_address",
    "npm_address",
    "token_id",
    "wallet",
    "wallet_source",
    "tick_lower",
    "tick_upper",
    "range_width_ticks",
    "range_width_pct",
    "is_full_range",
    "range_bucket",
    "fee_tier",
    "liquidity",
    "token0",
    "token1",
    "token0_decimals",
    "token1_decimals",
    "token0_symbol",
    "token1_symbol",
]


def _matches_pool(on_chain: dict, pool: PoolConfig) -> bool:
    if pool.token0_address is None or pool.token1_address is None or pool.fee_tier is None:
        return False
    return (
        on_chain["token0"].lower() == pool.token0_address.lower()
        and on_chain["token1"].lower() == pool.token1_address.lower()
        and on_chain["fee"] == pool.fee_tier
    )


def candidate_token_ids(events: pd.DataFrame) -> list[int]:
    """Prefer in-window liquidity changers, then Collect (often other pools)."""
    if events.empty:
        return []
    active = events[
        events["event_name"].isin(["IncreaseLiquidity", "DecreaseLiquidity", "Collect"])
    ]
    if active.empty:
        return []
    scored: dict[int, int] = {}
    for _, row in active.iterrows():
        tid = int(row["token_id"])
        if row["event_name"] == "IncreaseLiquidity":
            boost = 5
        elif row["event_name"] == "DecreaseLiquidity":
            boost = 4
        else:
            boost = 1
        scored[tid] = scored.get(tid, 0) + boost
    return sorted(scored, key=lambda t: (scored[t], t), reverse=True)


def resolve_wallet(
    rpc: RpcClient,
    npm: str,
    token_id: int,
    transfer_owners: dict[int, str],
) -> tuple[str | None, str]:
    """Prefer Transfer-fold wallet; else eth_call ownerOf(tokenId)."""
    if token_id in transfer_owners:
        return transfer_owners[token_id], "transfer"
    try:
        raw = rpc.eth_call(to=npm, data=owner_of_calldata(token_id))
        return decode_owner_of(raw), "owner_of"
    except Exception as exc:  # noqa: BLE001 — burned NFTs revert
        logger.debug("ownerOf(%s) failed: %s", token_id, exc)
        return None, "missing"


def build_nft_positions_frame(
    rpc: RpcClient,
    *,
    npm_address: str,
    pool: PoolConfig,
    events: pd.DataFrame,
    max_calls: int = 200,
    max_matches: int = 25,
) -> pd.DataFrame:
    """eth_call positions() for candidates; keep rows matching ``pool``."""
    owners = wallet_by_token_id(events)
    npm = to_checksum_address(npm_address)
    rows: list[dict] = []
    calls = 0

    for token_id in candidate_token_ids(events):
        if calls >= max_calls or len(rows) >= max_matches:
            break
        calls += 1
        try:
            raw = rpc.eth_call(to=npm, data=positions_calldata(token_id))
            on_chain = decode_positions(raw)
        except Exception as exc:  # noqa: BLE001 — burned NFTs are expected
            logger.debug("positions(%s) failed: %s", token_id, exc)
            continue
        if not _matches_pool(on_chain, pool):
            continue

        width = on_chain["tick_upper"] - on_chain["tick_lower"]
        full = is_full_range(width, on_chain["tick_lower"], on_chain["tick_upper"])
        wallet, wallet_source = resolve_wallet(rpc, npm, token_id, owners)

        rows.append(
            {
                "pool_name": pool.name,
                "pool_address": to_checksum_address(pool.address),
                "npm_address": npm,
                "token_id": token_id,
                "wallet": wallet,
                "wallet_source": wallet_source,
                "tick_lower": on_chain["tick_lower"],
                "tick_upper": on_chain["tick_upper"],
                "range_width_ticks": width,
                "range_width_pct": None if full else range_width_pct(width),
                "is_full_range": full,
                "range_bucket": range_bucket(width),
                "fee_tier": on_chain["fee"],
                "liquidity": on_chain["liquidity"],
                "token0": on_chain["token0"],
                "token1": on_chain["token1"],
                "token0_decimals": pool.token0_decimals,
                "token1_decimals": pool.token1_decimals,
                "token0_symbol": pool.token0_symbol,
                "token1_symbol": pool.token1_symbol,
            }
        )

    logger.info(
        "NFT snapshot scan: calls=%d matches=%d pool=%s",
        calls,
        len(rows),
        pool.name,
    )
    return pd.DataFrame(rows)


def write_nft_positions_snapshot(
    rpc: RpcClient,
    data_dir: Path,
    npm_address: str,
    pool: PoolConfig,
    *,
    max_calls: int = 200,
    max_matches: int = 25,
) -> Path | None:
    events = load_npm_events(data_dir, npm_address)
    frame = build_nft_positions_frame(
        rpc,
        npm_address=npm_address,
        pool=pool,
        events=events,
        max_calls=max_calls,
        max_matches=max_matches,
    )
    out_dir = data_dir / "analytics" / "nft_positions" / f"pool={to_checksum_address(pool.address)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "positions.parquet"
    if frame.empty:
        logger.warning("No pool-matched NFT positions for %s", pool.name)
        pd.DataFrame(columns=SNAPSHOT_COLUMNS).to_parquet(path, index=False)
        return path

    frame.to_parquet(path, index=False)
    logger.info("Wrote %d NFT positions → %s", len(frame), path)
    return path
