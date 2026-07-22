"""Uniswap V2 event topics and ABI decoding."""

from __future__ import annotations

from typing import Any

from eth_abi import decode
from eth_utils import event_abi_to_log_topic, to_checksum_address
from web3 import Web3

# Minimal V2 Pair ABI for the four events we index + getReserves.
PAIR_ABI: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": False, "name": "amount0In", "type": "uint256"},
            {"indexed": False, "name": "amount1In", "type": "uint256"},
            {"indexed": False, "name": "amount0Out", "type": "uint256"},
            {"indexed": False, "name": "amount1Out", "type": "uint256"},
            {"indexed": True, "name": "to", "type": "address"},
        ],
        "name": "Swap",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "Mint",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
            {"indexed": True, "name": "to", "type": "address"},
        ],
        "name": "Burn",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "reserve0", "type": "uint112"},
            {"indexed": False, "name": "reserve1", "type": "uint112"},
        ],
        "name": "Sync",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "reserve0", "type": "uint112"},
            {"name": "reserve1", "type": "uint112"},
            {"name": "blockTimestampLast", "type": "uint32"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

_EVENT_BY_TOPIC: dict[str, dict[str, Any]] = {}
for _item in PAIR_ABI:
    if _item.get("type") == "event":
        topic = "0x" + event_abi_to_log_topic(_item).hex()
        _EVENT_BY_TOPIC[topic.lower()] = _item

GET_RESERVES_SELECTOR = Web3.keccak(text="getReserves()")[:4].hex()
GET_RESERVES_DATA = "0x" + GET_RESERVES_SELECTOR


def topic0_set() -> list[str]:
    return list(_EVENT_BY_TOPIC.keys())


def _topic_address(topic: str) -> str:
    return to_checksum_address("0x" + topic[-40:])


def decode_log(raw: dict[str, Any], pool_address: str) -> dict[str, Any] | None:
    """Decode a raw eth_getLogs entry into a flat event row, or None if unknown."""
    topics = raw.get("topics") or []
    if not topics:
        return None
    topic0 = topics[0].lower()
    abi = _EVENT_BY_TOPIC.get(topic0)
    if abi is None:
        return None

    name = abi["name"]
    data_hex = raw.get("data", "0x")
    data_bytes = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)

    non_indexed = [inp["type"] for inp in abi["inputs"] if not inp.get("indexed")]
    decoded_data = decode(non_indexed, data_bytes) if non_indexed else ()

    values: dict[str, Any] = {}
    data_i = 0
    topic_i = 1
    for inp in abi["inputs"]:
        if inp.get("indexed"):
            values[inp["name"]] = _topic_address(topics[topic_i])
            topic_i += 1
        else:
            values[inp["name"]] = decoded_data[data_i]
            data_i += 1

    row: dict[str, Any] = {
        "pool_address": to_checksum_address(pool_address),
        "event_name": name,
        "block_number": int(raw["blockNumber"], 16),
        "log_index": int(raw["logIndex"], 16),
        "tx_hash": raw["transactionHash"],
        "reserve0": None,
        "reserve1": None,
        "amount0_in": None,
        "amount1_in": None,
        "amount0_out": None,
        "amount1_out": None,
        "amount0": None,
        "amount1": None,
        "sender": values.get("sender"),
        "to_address": values.get("to"),
    }

    if name == "Sync":
        row["reserve0"] = str(values["reserve0"])
        row["reserve1"] = str(values["reserve1"])
    elif name == "Swap":
        row["amount0_in"] = str(values["amount0In"])
        row["amount1_in"] = str(values["amount1In"])
        row["amount0_out"] = str(values["amount0Out"])
        row["amount1_out"] = str(values["amount1Out"])
    elif name in ("Mint", "Burn"):
        row["amount0"] = str(values["amount0"])
        row["amount1"] = str(values["amount1"])

    return row


def decode_get_reserves(result_hex: str) -> tuple[int, int, int]:
    raw = bytes.fromhex(result_hex[2:] if result_hex.startswith("0x") else result_hex)
    reserve0, reserve1, ts = decode(["uint112", "uint112", "uint32"], raw)
    return int(reserve0), int(reserve1), int(ts)
