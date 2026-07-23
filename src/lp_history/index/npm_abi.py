"""Uniswap V3 NonfungiblePositionManager ABI decode + positions() call."""

from __future__ import annotations

from typing import Any

from eth_abi import decode, encode
from eth_utils import event_abi_to_log_topic, to_checksum_address
from web3 import Web3

NPM_ABI: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": True, "name": "tokenId", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "tokenId", "type": "uint256"},
            {"indexed": False, "name": "liquidity", "type": "uint128"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "IncreaseLiquidity",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "tokenId", "type": "uint256"},
            {"indexed": False, "name": "liquidity", "type": "uint128"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "DecreaseLiquidity",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "tokenId", "type": "uint256"},
            {"indexed": False, "name": "recipient", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "Collect",
        "type": "event",
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "positions",
        "outputs": [
            {"name": "nonce", "type": "uint96"},
            {"name": "operator", "type": "address"},
            {"name": "token0", "type": "address"},
            {"name": "token1", "type": "address"},
            {"name": "fee", "type": "uint24"},
            {"name": "tickLower", "type": "int24"},
            {"name": "tickUpper", "type": "int24"},
            {"name": "liquidity", "type": "uint128"},
            {"name": "feeGrowthInside0LastX128", "type": "uint256"},
            {"name": "feeGrowthInside1LastX128", "type": "uint256"},
            {"name": "tokensOwed0", "type": "uint128"},
            {"name": "tokensOwed1", "type": "uint128"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

_EVENT_BY_TOPIC: dict[str, dict[str, Any]] = {}
for _item in NPM_ABI:
    if _item.get("type") == "event":
        topic = "0x" + event_abi_to_log_topic(_item).hex()
        _EVENT_BY_TOPIC[topic.lower()] = _item

POSITIONS_SELECTOR = Web3.keccak(text="positions(uint256)")[:4]


def topic0_set() -> list[str]:
    return list(_EVENT_BY_TOPIC.keys())


def _topic_address(topic: str) -> str:
    return to_checksum_address("0x" + topic[-40:])


def _topic_uint256(topic: str) -> int:
    return int(topic, 16)


def _decode_indexed(inp: dict[str, Any], topic: str) -> Any:
    t = inp["type"]
    if t == "address":
        return _topic_address(topic)
    if t == "uint256":
        return _topic_uint256(topic)
    raise ValueError(f"Unsupported indexed type: {t}")


def decode_log(raw: dict[str, Any], npm_address: str) -> dict[str, Any] | None:
    topics = raw.get("topics") or []
    if not topics:
        return None
    abi = _EVENT_BY_TOPIC.get(topics[0].lower())
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
        "contract_address": to_checksum_address(npm_address),
        "protocol": "uniswap_v3_npm",
        "event_name": name,
        "block_number": int(raw["blockNumber"], 16),
        "log_index": int(raw["logIndex"], 16),
        "tx_hash": raw["transactionHash"],
        "token_id": None,
        "from_address": None,
        "to_address": None,
        "liquidity": None,
        "amount0": None,
        "amount1": None,
        "recipient": None,
    }

    if name == "Transfer":
        row["from_address"] = values["from"]
        row["to_address"] = values["to"]
        row["token_id"] = str(values["tokenId"])
    elif name in ("IncreaseLiquidity", "DecreaseLiquidity"):
        row["token_id"] = str(values["tokenId"])
        row["liquidity"] = str(values["liquidity"])
        row["amount0"] = str(values["amount0"])
        row["amount1"] = str(values["amount1"])
    elif name == "Collect":
        row["token_id"] = str(values["tokenId"])
        row["recipient"] = to_checksum_address(values["recipient"])
        row["amount0"] = str(values["amount0"])
        row["amount1"] = str(values["amount1"])

    return row


def positions_calldata(token_id: int) -> str:
    return "0x" + (bytes(POSITIONS_SELECTOR) + encode(["uint256"], [token_id])).hex()


def decode_positions(result_hex: str) -> dict[str, Any]:
    raw = bytes.fromhex(result_hex[2:] if result_hex.startswith("0x") else result_hex)
    decoded = decode(
        [
            "uint96",
            "address",
            "address",
            "address",
            "uint24",
            "int24",
            "int24",
            "uint128",
            "uint256",
            "uint256",
            "uint128",
            "uint128",
        ],
        raw,
    )
    return {
        "nonce": int(decoded[0]),
        "operator": to_checksum_address(decoded[1]),
        "token0": to_checksum_address(decoded[2]),
        "token1": to_checksum_address(decoded[3]),
        "fee": int(decoded[4]),
        "tick_lower": int(decoded[5]),
        "tick_upper": int(decoded[6]),
        "liquidity": int(decoded[7]),
        "fee_growth_inside0_last_x128": int(decoded[8]),
        "fee_growth_inside1_last_x128": int(decoded[9]),
        "tokens_owed0": int(decoded[10]),
        "tokens_owed1": int(decoded[11]),
    }
