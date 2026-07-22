"""Hive-partitioned Parquet event store."""

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
    pool_address: str,
    ingested_date: dt.date | None = None,
) -> Path:
    """Append-style write under data/events/pool=<addr>/ingested_date=YYYY-MM-DD/."""
    if frame.empty:
        raise ValueError("Cannot write empty event frame")

    ingested_date = ingested_date or dt.datetime.now(dt.UTC).date()
    addr = to_checksum_address(pool_address)
    partition = (
        data_dir / "events" / f"pool={addr}" / f"ingested_date={ingested_date.isoformat()}"
    )
    partition.mkdir(parents=True, exist_ok=True)

    min_block = int(frame["block_number"].min())
    max_block = int(frame["block_number"].max())
    path = partition / f"blocks_{min_block}_{max_block}.parquet"
    frame.to_parquet(path, index=False)
    logger.info("Wrote %d events to %s", len(frame), path)
    return path


def read_all_events(data_dir: Path, pool_address: str) -> pd.DataFrame:
    addr = to_checksum_address(pool_address)
    paths = sorted(data_dir.glob(f"events/pool={addr}/*/*.parquet"))
    if not paths:
        return pd.DataFrame()
    frames = [pd.read_parquet(p) for p in paths]
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["block_number", "log_index"], keep="last")
    return out.sort_values(["block_number", "log_index"]).reset_index(drop=True)
