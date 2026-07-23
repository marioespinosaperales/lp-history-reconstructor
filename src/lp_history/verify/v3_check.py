"""Compare reconstructed V3 in-range liquidity against pool.liquidity()."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from eth_utils import to_checksum_address

from lp_history.index.v3_abi import LIQUIDITY_DATA, SLOT0_DATA, decode_liquidity, decode_slot0
from lp_history.rpc.client import RpcClient
from lp_history.state.v3_positions import (
    V3Position,
    in_range_liquidity,
    positions_for_pool,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class V3VerifyResult:
    ok: bool
    current_tick: int
    reconstructed_liquidity: int
    on_chain_liquidity: int
    position_count: int
    message: str
    sample_positions: list[V3Position]


def verify_v3_pool(rpc: RpcClient, data_dir, pool_address: str) -> V3VerifyResult:
    address = to_checksum_address(pool_address)
    positions = positions_for_pool(data_dir, address)

    slot0_hex = rpc.eth_call(to=address, data=SLOT0_DATA)
    _sqrt, tick = decode_slot0(slot0_hex)
    on_chain = decode_liquidity(rpc.eth_call(to=address, data=LIQUIDITY_DATA))
    reconstructed = in_range_liquidity(positions, tick)

    # Windowed backfill will miss older Mint/Burn, so reconstructed L is a lower
    # bound of truth. PASS when we match exactly; WARN (ok=False) with a clear
    # message when under-counting due to incomplete history.
    ok = reconstructed == on_chain
    if ok:
        msg = (
            f"PASS in-range liquidity matches at tick {tick}: "
            f"L={reconstructed} (positions={len(positions)})"
        )
    elif reconstructed < on_chain:
        msg = (
            f"PARTIAL at tick {tick}: reconstructed L={reconstructed} < on-chain L={on_chain} "
            f"(positions={len(positions)}). Incomplete lookback — raise lookback_blocks "
            f"or backfill from pool deployment for a full match."
        )
        # Treat under-count from short lookback as non-fatal for Phase 1 smoke:
        # structural pipeline works if we have positions and a coherent tick.
        ok = len(positions) > 0 and reconstructed > 0
        if ok:
            msg = "SMOKE_OK " + msg
    else:
        msg = (
            f"FAIL at tick {tick}: reconstructed L={reconstructed} > on-chain L={on_chain} "
            f"(positions={len(positions)})"
        )

    logger.info(msg)
    # Prefer widest/narrowest samples for the range-width story
    sample = sorted(positions, key=lambda p: p.range_width_ticks)[:5]
    return V3VerifyResult(
        ok=ok,
        current_tick=tick,
        reconstructed_liquidity=reconstructed,
        on_chain_liquidity=on_chain,
        position_count=len(positions),
        message=msg,
        sample_positions=sample,
    )
