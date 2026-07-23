"""Build tokenId → wallet map and position liquidity from NPM events."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from eth_utils import to_checksum_address

from lp_history.load.parquet import read_all_events

# Zero address used in ERC-721 mint Transfers
ZERO = "0x0000000000000000000000000000000000000000"


@dataclass(frozen=True)
class NftPosition:
    token_id: int
    wallet: str
    liquidity: int
    tick_lower: int | None = None
    tick_upper: int | None = None
    fee: int | None = None
    token0: str | None = None
    token1: str | None = None

    @property
    def range_width_ticks(self) -> int | None:
        if self.tick_lower is None or self.tick_upper is None:
            return None
        return self.tick_upper - self.tick_lower


def wallet_by_token_id(events: pd.DataFrame) -> dict[int, str]:
    """Latest non-burn Transfer.to wins as the current NFT owner."""
    if events.empty:
        return {}
    transfers = events[events["event_name"] == "Transfer"].copy()
    if transfers.empty:
        return {}
    transfers = transfers.sort_values(["block_number", "log_index"])
    owners: dict[int, str] = {}
    for _, row in transfers.iterrows():
        token_id = int(row["token_id"])
        to_addr = to_checksum_address(row["to_address"])
        if to_addr == ZERO:
            owners.pop(token_id, None)
        else:
            owners[token_id] = to_addr
    return owners


def liquidity_by_token_id(events: pd.DataFrame) -> dict[int, int]:
    """Net liquidity from IncreaseLiquidity (+) / DecreaseLiquidity (-)."""
    if events.empty:
        return {}
    liq_events = events[
        events["event_name"].isin(["IncreaseLiquidity", "DecreaseLiquidity"])
    ].copy()
    if liq_events.empty:
        return {}
    liq_events = liq_events.sort_values(["block_number", "log_index"])
    balances: dict[int, int] = {}
    for _, row in liq_events.iterrows():
        token_id = int(row["token_id"])
        delta = int(row["liquidity"])
        if row["event_name"] == "DecreaseLiquidity":
            delta = -delta
        balances[token_id] = balances.get(token_id, 0) + delta
    return balances


def nft_positions_from_events(events: pd.DataFrame) -> list[NftPosition]:
    owners = wallet_by_token_id(events)
    liqs = liquidity_by_token_id(events)
    token_ids = sorted(set(owners) | set(liqs))
    return [
        NftPosition(
            token_id=tid,
            wallet=owners.get(tid, ZERO),
            liquidity=max(liqs.get(tid, 0), 0),
        )
        for tid in token_ids
        if tid in owners
    ]


def load_npm_events(data_dir, npm_address: str) -> pd.DataFrame:
    return read_all_events(data_dir, npm_address, kind="npm")
