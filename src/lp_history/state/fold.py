"""Reconstruct pool reserves by folding Sync events in order.

Uniswap V2 emits Sync after every reserve change with the absolute
(reserve0, reserve1). The latest Sync at or before a block IS the state —
no need to replay Swap/Mint/Burn arithmetic for reserves.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lp_history.load.parquet import read_all_events


@dataclass(frozen=True)
class PoolReserves:
    reserve0: int
    reserve1: int
    block_number: int
    log_index: int


def latest_reserves_from_events(events: pd.DataFrame) -> PoolReserves | None:
    if events.empty:
        return None
    syncs = events[events["event_name"] == "Sync"].copy()
    if syncs.empty:
        return None
    syncs = syncs.sort_values(["block_number", "log_index"])
    last = syncs.iloc[-1]
    return PoolReserves(
        reserve0=int(last["reserve0"]),
        reserve1=int(last["reserve1"]),
        block_number=int(last["block_number"]),
        log_index=int(last["log_index"]),
    )


def latest_reserves_for_pool(data_dir, pool_address: str) -> PoolReserves | None:
    events = read_all_events(data_dir, pool_address)
    return latest_reserves_from_events(events)
