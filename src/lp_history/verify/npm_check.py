"""Verify NPM positions against on-chain positions(tokenId) for a target pool."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from eth_utils import to_checksum_address

from lp_history.index.npm_abi import decode_positions, positions_calldata
from lp_history.rpc.client import RpcClient
from lp_history.settings import PoolConfig
from lp_history.state.npm_wallets import (
    NftPosition,
    liquidity_by_token_id,
    load_npm_events,
    wallet_by_token_id,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NpmVerifyResult:
    ok: bool
    checked: int
    matched: int
    pool_positions: int
    message: str
    samples: list[NftPosition]


def _matches_pool(on_chain: dict, pool: PoolConfig) -> bool:
    if pool.token0_address is None or pool.token1_address is None or pool.fee_tier is None:
        return False
    return (
        on_chain["token0"].lower() == pool.token0_address.lower()
        and on_chain["token1"].lower() == pool.token1_address.lower()
        and on_chain["fee"] == pool.fee_tier
    )


def verify_npm_for_pool(
    rpc: RpcClient,
    data_dir,
    npm_address: str,
    pool: PoolConfig,
    *,
    sample_size: int = 5,
) -> NpmVerifyResult:
    """Filter NPM tokenIds to ``pool``, compare event liquidity vs positions()."""
    events = load_npm_events(data_dir, npm_address)
    owners = wallet_by_token_id(events)
    event_liq = liquidity_by_token_id(events)

    if not owners:
        return NpmVerifyResult(
            ok=False,
            checked=0,
            matched=0,
            pool_positions=0,
            message="No NPM Transfer events in window — nothing to verify",
            samples=[],
        )

    npm = to_checksum_address(npm_address)
    pool_positions: list[NftPosition] = []
    matched = 0
    checked = 0

    # Prefer tokenIds that also saw liquidity changes in-window (richer signal)
    candidate_ids = sorted(set(owners) & set(event_liq), reverse=True)
    if not candidate_ids:
        candidate_ids = sorted(owners, reverse=True)

    for token_id in candidate_ids:
        if len(pool_positions) >= sample_size * 3:
            # Cap RPC calls on free tier
            break
        try:
            raw = rpc.eth_call(to=npm, data=positions_calldata(token_id))
            on_chain = decode_positions(raw)
        except Exception as exc:  # noqa: BLE001 — burned/invalid tokenIds happen
            logger.debug("positions(%s) failed: %s", token_id, exc)
            continue

        if not _matches_pool(on_chain, pool):
            continue

        checked += 1
        reconstructed = event_liq.get(token_id, 0)
        wallet = owners[token_id]
        pos = NftPosition(
            token_id=token_id,
            wallet=wallet,
            liquidity=on_chain["liquidity"],
            tick_lower=on_chain["tick_lower"],
            tick_upper=on_chain["tick_upper"],
            fee=on_chain["fee"],
            token0=on_chain["token0"],
            token1=on_chain["token1"],
        )
        pool_positions.append(pos)

        # Event-sourced L is a lower bound under short lookback; exact match is ideal.
        if reconstructed == on_chain["liquidity"]:
            matched += 1
        elif reconstructed > 0 and reconstructed <= on_chain["liquidity"]:
            matched += 1  # partial history still coherent

        if checked >= sample_size:
            break

    samples = sorted(
        pool_positions,
        key=lambda p: p.range_width_ticks or 10**9,
    )[:sample_size]

    if checked == 0:
        msg = (
            f"No NPM positions in window matched pool {pool.name} "
            f"(token0/token1/fee). Try a larger lookback_blocks."
        )
        ok = False
    elif matched == checked:
        msg = (
            f"SMOKE_OK npm↔pool {pool.name}: checked={checked} "
            f"wallet-attributed positions with range widths"
        )
        ok = True
    else:
        msg = (
            f"PARTIAL npm↔pool {pool.name}: matched={matched}/{checked} "
            f"(short lookback can under-count event liquidity)"
        )
        ok = matched > 0

    logger.info(msg)
    return NpmVerifyResult(
        ok=ok,
        checked=checked,
        matched=matched,
        pool_positions=len(pool_positions),
        message=msg,
        samples=samples,
    )
