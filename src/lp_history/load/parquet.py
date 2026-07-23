"""Hive-partitioned Parquet event store (pools + NPM)."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import pandas as pd
from eth_utils import to_checksum_address

logger = logging.getLogger(__name__)


def write_events(
    frame: pd.DataFrame,
    data_dir: Path,
    address: str,
    *,
    kind: str = "pool",
    ingested_date: dt.date | None = None,
) -> Path:
    """Write under data/<kind>/address=<addr>/ingested_date=YYYY-MM-DD/.

    ``kind`` is ``pool`` (V2/V3 pool logs) or ``npm`` (position manager logs).
    Legacy pool paths used ``pool=<addr>``; we keep writing that for pools so
    existing checkpoints/data keep working.
    """
    if frame.empty:
        raise ValueError("Cannot write empty event frame")

    ingested_date = ingested_date or dt.datetime.now(dt.UTC).date()
    addr = to_checksum_address(address)
    if kind == "pool":
        partition = (
            data_dir / "events" / f"pool={addr}" / f"ingested_date={ingested_date.isoformat()}"
        )
    elif kind == "npm":
        partition = (
            data_dir / "npm" / f"address={addr}" / f"ingested_date={ingested_date.isoformat()}"
        )
    else:
        raise ValueError(f"Unknown event kind: {kind}")

    partition.mkdir(parents=True, exist_ok=True)
    min_block = int(frame["block_number"].min())
    max_block = int(frame["block_number"].max())
    path = partition / f"blocks_{min_block}_{max_block}.parquet"
    frame.to_parquet(path, index=False)
    logger.info("Wrote %d events to %s", len(frame), path)
    return path


def read_all_events(data_dir: Path, address: str, *, kind: str = "pool") -> pd.DataFrame:
    addr = to_checksum_address(address)
    if kind == "pool":
        paths = sorted(data_dir.glob(f"events/pool={addr}/*/*.parquet"))
    elif kind == "npm":
        paths = sorted(data_dir.glob(f"npm/address={addr}/*/*.parquet"))
    else:
        raise ValueError(f"Unknown event kind: {kind}")

    if not paths:
        return pd.DataFrame()
    frames = [pd.read_parquet(p) for p in paths]
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["block_number", "log_index"], keep="last")
    return out.sort_values(["block_number", "log_index"]).reset_index(drop=True)
