"""Uniswap V3 pool event topics and ABI decoding."""

from __future__ import annotations

from typing import Any

from eth_abi import decode
from eth_utils import event_abi_to_log_topic, to_checksum_address
from web3 import Web3

# Minimal V3 Pool ABI: Mint / Burn / Swap / Collect + liquidity() + slot0().
POOL_ABI: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "sender", "type": "address"},
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "tickLower", "type": "int24"},
            {"indexed": True, "name": "tickUpper", "type": "int24"},
            {"indexed": False, "name": "amount", "type": "uint128"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "Mint",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "tickLower", "type": "int24"},
            {"indexed": True, "name": "tickUpper", "type": "int24"},
            {"indexed": False, "name": "amount", "type": "uint128"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "Burn",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": True, "name": "recipient", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "int256"},
            {"indexed": False, "name": "amount1", "type": "int256"},
            {"indexed": False, "name": "sqrtPriceX96", "type": "uint160"},
            {"indexed": False, "name": "liquidity", "type": "uint128"},
            {"indexed": False, "name": "tick", "type": "int24"},
        ],
        "name": "Swap",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": False, "name": "recipient", "type": "address"},
            {"indexed": True, "name": "tickLower", "type": "int24"},
            {"indexed": True, "name": "tickUpper", "type": "int24"},
            {"indexed": False, "name": "amount0", "type": "uint128"},
            {"indexed": False, "name": "amount1", "type": "uint128"},
        ],
        "name": "Collect",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"name": "sqrtPriceX96", "type": "uint160"},
            {"name": "tick", "type": "int24"},
            {"name": "observationIndex", "type": "uint16"},
            {"name": "observationCardinality", "type": "uint16"},
            {"name": "observationCardinalityNext", "type": "uint16"},
            {"name": "feeProtocol", "type": "uint8"},
            {"name": "unlocked", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

_EVENT_BY_TOPIC: dict[str, dict[str, Any]] = {}
for _item in POOL_ABI:
    if _item.get("type") == "event":
        topic = "0x" + event_abi_to_log_topic(_item).hex()
        _EVENT_BY_TOPIC[topic.lower()] = _item

LIQUIDITY_DATA = "0x" + Web3.keccak(text="liquidity()")[:4].hex()
SLOT0_DATA = "0x" + Web3.keccak(text="slot0()")[:4].hex()


def topic0_set() -> list[str]:
    return list(_EVENT_BY_TOPIC.keys())


def _topic_address(topic: str) -> str:
    return to_checksum_address("0x" + topic[-40:])


def _topic_int24(topic: str) -> int:
    """Decode an indexed int24 from a 32-byte topic (sign-extended)."""
    value = int(topic, 16)
    if value >= 2**255:
        value -= 2**256
    return value


def _decode_indexed(inp: dict[str, Any], topic: str) -> Any:
    t = inp["type"]
    if t == "address":
        return _topic_address(topic)
    if t == "int24":
        return _topic_int24(topic)
    raise ValueError(f"Unsupported indexed type: {t}")


def decode_log(raw: dict[str, Any], pool_address: str) -> dict[str, Any] | None:
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
            values[inp["name"]] = _decode_indexed(inp, topics[topic_i])
            topic_i += 1
        else:
            values[inp["name"]] = decoded_data[data_i]
            data_i += 1

    row: dict[str, Any] = {
        "pool_address": to_checksum_address(pool_address),
        "protocol": "uniswap_v3",
        "event_name": name,
        "block_number": int(raw["blockNumber"], 16),
        "log_index": int(raw["logIndex"], 16),
        "tx_hash": raw["transactionHash"],
        # V2-compat placeholders
        "reserve0": None,
        "reserve1": None,
        "amount0_in": None,
        "amount1_in": None,
        "amount0_out": None,
        "amount1_out": None,
        "amount0": None,
        "amount1": None,
        "sender": values.get("sender"),
        "to_address": values.get("recipient") or values.get("to"),
        # V3 fields
        "owner": values.get("owner"),
        "tick_lower": values.get("tickLower"),
        "tick_upper": values.get("tickUpper"),
        "liquidity": None,
        "sqrt_price_x96": None,
        "tick": values.get("tick"),
        "recipient": values.get("recipient"),
    }

    if name in ("Mint", "Burn"):
        row["liquidity"] = str(values["amount"])
        row["amount0"] = str(values["amount0"])
        row["amount1"] = str(values["amount1"])
    elif name == "Swap":
        row["amount0"] = str(values["amount0"])
        row["amount1"] = str(values["amount1"])
        row["sqrt_price_x96"] = str(values["sqrtPriceX96"])
        row["liquidity"] = str(values["liquidity"])
        row["tick"] = int(values["tick"])
    elif name == "Collect":
        row["amount0"] = str(values["amount0"])
        row["amount1"] = str(values["amount1"])

    return row


def decode_liquidity(result_hex: str) -> int:
    raw = bytes.fromhex(result_hex[2:] if result_hex.startswith("0x") else result_hex)
    (liq,) = decode(["uint128"], raw)
    return int(liq)


def decode_slot0(result_hex: str) -> tuple[int, int]:
    """Return (sqrt_price_x96, tick)."""
    raw = bytes.fromhex(result_hex[2:] if result_hex.startswith("0x") else result_hex)
    sqrt_price, tick, *_rest = decode(
        ["uint160", "int24", "uint16", "uint16", "uint16", "uint8", "bool"], raw
    )
    return int(sqrt_price), int(tick)
