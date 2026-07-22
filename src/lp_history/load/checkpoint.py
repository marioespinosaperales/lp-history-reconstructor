"""Checkpoint persistence: last fully processed block per pool."""

from __future__ import annotations

import json
from pathlib import Path

from eth_utils import to_checksum_address


def _path(checkpoint_dir: Path, pool_address: str) -> Path:
    addr = to_checksum_address(pool_address).lower().replace("0x", "")
    return checkpoint_dir / f"{addr}.json"


def load_checkpoint(checkpoint_dir: Path, pool_address: str) -> int | None:
    path = _path(checkpoint_dir, pool_address)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return int(data["last_block"])


def save_checkpoint(checkpoint_dir: Path, pool_address: str, last_block: int) -> Path:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    path = _path(checkpoint_dir, pool_address)
    path.write_text(
        json.dumps({"pool": to_checksum_address(pool_address), "last_block": last_block}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return path
