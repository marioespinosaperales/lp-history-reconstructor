"""Compare reconstructed reserves against on-chain getReserves()."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from eth_utils import to_checksum_address

from lp_history.index.abi import GET_RESERVES_DATA, decode_get_reserves
from lp_history.rpc.client import RpcClient
from lp_history.state.fold import PoolReserves, latest_reserves_for_pool

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    block_number: int
    reconstructed: PoolReserves | None
    on_chain: tuple[int, int] | None
    message: str


def fetch_on_chain_reserves(
    rpc: RpcClient, pool_address: str, block_number: int
) -> tuple[int, int]:
    result = rpc.eth_call(
        to=to_checksum_address(pool_address),
        data=GET_RESERVES_DATA,
        block=block_number,
    )
    r0, r1, _ts = decode_get_reserves(result)
    return r0, r1


def verify_pool(
    rpc: RpcClient,
    data_dir,
    pool_address: str,
    *,
    at_block: int | None = None,
) -> VerifyResult:
    reconstructed = latest_reserves_for_pool(data_dir, pool_address)
    if reconstructed is None:
        return VerifyResult(
            ok=False,
            block_number=at_block or 0,
            reconstructed=None,
            on_chain=None,
            message="No Sync events found — nothing to verify",
        )

    block = at_block if at_block is not None else reconstructed.block_number
    on_chain = fetch_on_chain_reserves(rpc, pool_address, block)

    # Exact match on uint reserves (event sourcing must be bit-identical).
    ok = (
        reconstructed.reserve0 == on_chain[0]
        and reconstructed.reserve1 == on_chain[1]
        and reconstructed.block_number == block
    )
    # If we verify at a later tip block than the last Sync, reserves should still
    # match only if no Sync happened after — use the Sync block for apples-to-apples.
    if at_block is not None and at_block != reconstructed.block_number:
        on_chain_at_sync = fetch_on_chain_reserves(rpc, pool_address, reconstructed.block_number)
        ok = (
            reconstructed.reserve0 == on_chain_at_sync[0]
            and reconstructed.reserve1 == on_chain_at_sync[1]
        )
        on_chain = on_chain_at_sync
        block = reconstructed.block_number

    msg = (
        f"PASS reserves match at block {block}: "
        f"r0={reconstructed.reserve0} r1={reconstructed.reserve1}"
        if ok
        else (
            f"FAIL at block {block}: reconstructed=({reconstructed.reserve0}, "
            f"{reconstructed.reserve1}) on_chain={on_chain}"
        )
    )
    logger.info(msg)
    return VerifyResult(
        ok=ok,
        block_number=block,
        reconstructed=reconstructed,
        on_chain=on_chain,
        message=msg,
    )
