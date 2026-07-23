"""Protocol-aware event decode helpers."""

from __future__ import annotations

from typing import Any

from lp_history.index import abi as v2_abi
from lp_history.index import v3_abi


def topic0_set(protocol: str) -> list[str]:
    if protocol == "uniswap_v3":
        return v3_abi.topic0_set()
    if protocol == "uniswap_v2":
        return v2_abi.topic0_set()
    raise ValueError(f"Unsupported protocol: {protocol}")


def decode_log(raw: dict[str, Any], pool_address: str, protocol: str) -> dict[str, Any] | None:
    if protocol == "uniswap_v3":
        return v3_abi.decode_log(raw, pool_address)
    if protocol == "uniswap_v2":
        return v2_abi.decode_log(raw, pool_address)
    raise ValueError(f"Unsupported protocol: {protocol}")
