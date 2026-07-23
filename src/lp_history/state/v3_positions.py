"""Reconstruct Uniswap V3 positions and in-range liquidity from Mint/Burn."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lp_history.load.parquet import read_all_events


@dataclass(frozen=True)
class V3Position:
    owner: str
    tick_lower: int
    tick_upper: int
    liquidity: int

    @property
    def range_width_ticks(self) -> int:
        return self.tick_upper - self.tick_lower


def positions_from_events(events: pd.DataFrame) -> list[V3Position]:
    """Net liquidity per (owner, tickLower, tickUpper) after Mint(+)/Burn(-)."""
    if events.empty:
        return []
    mb = events[events["event_name"].isin(["Mint", "Burn"])].copy()
    if mb.empty:
        return []

    balances: dict[tuple[str, int, int], int] = {}
    mb = mb.sort_values(["block_number", "log_index"])
    for _, row in mb.iterrows():
        key = (str(row["owner"]), int(row["tick_lower"]), int(row["tick_upper"]))
        delta = int(row["liquidity"])
        if row["event_name"] == "Burn":
            delta = -delta
        balances[key] = balances.get(key, 0) + delta

    out: list[V3Position] = []
    for (owner, lo, hi), liq in balances.items():
        if liq > 0:
            out.append(V3Position(owner=owner, tick_lower=lo, tick_upper=hi, liquidity=liq))
    return out


def in_range_liquidity(positions: list[V3Position], current_tick: int) -> int:
    """Active liquidity at ``current_tick`` (tickLower <= tick < tickUpper)."""
    total = 0
    for pos in positions:
        if pos.tick_lower <= current_tick < pos.tick_upper:
            total += pos.liquidity
    return total


def positions_for_pool(data_dir, pool_address: str) -> list[V3Position]:
    return positions_from_events(read_all_events(data_dir, pool_address))
