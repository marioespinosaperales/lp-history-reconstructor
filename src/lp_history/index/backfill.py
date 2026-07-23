"""Chunked pool event backfill via eth_getLogs (V2 + V3)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from eth_utils import to_checksum_address

from lp_history.index.decode import decode_log, topic0_set
from lp_history.load.checkpoint import load_checkpoint, save_checkpoint
from lp_history.load.parquet import write_events
from lp_history.rpc.client import RpcClient
from lp_history.settings import PipelineConfig, PoolConfig

logger = logging.getLogger(__name__)


def resolve_range(
    rpc: RpcClient,
    pipeline: PipelineConfig,
    address: str,
    checkpoint_dir: Path,
) -> tuple[int, int]:
    """Return (from_block, to_block_inclusive) for this run."""
    tip = rpc.block_number()
    to_block = tip - pipeline.confirmations
    if to_block < 0:
        raise RuntimeError("Chain tip is below confirmation depth")

    checkpoint = load_checkpoint(checkpoint_dir, address)
    if checkpoint is not None:
        from_block = checkpoint + 1
    else:
        from_block = max(0, to_block - pipeline.lookback_blocks + 1)

    return from_block, to_block


def backfill_pool(
    rpc: RpcClient,
    pool: PoolConfig,
    pipeline: PipelineConfig,
) -> dict[str, int]:
    """Index events for one pool over the resolved window. Returns stats."""
    address = to_checksum_address(pool.address)
    from_block, to_block = resolve_range(rpc, pipeline, address, pipeline.checkpoint_dir)

    if from_block > to_block:
        logger.info(
            "%s already caught up (checkpoint >= tip-%d)", pool.name, pipeline.confirmations
        )
        return {"events": 0, "from_block": from_block, "to_block": to_block, "chunks": 0}

    topics = {t.lower() for t in topic0_set(pool.protocol)}
    total_events = 0
    chunks = 0
    cursor = from_block

    logger.info(
        "Backfilling %s [%s] (%s) blocks %d..%d (chunk=%d)",
        pool.name,
        pool.protocol,
        address,
        from_block,
        to_block,
        pipeline.chunk_size,
    )

    while cursor <= to_block:
        end = min(cursor + pipeline.chunk_size - 1, to_block)
        raw_logs = rpc.get_logs(address=address, from_block=cursor, to_block=end)
        rows = []
        for raw in raw_logs:
            topic0 = (raw.get("topics") or [None])[0]
            if topic0 is None or topic0.lower() not in topics:
                continue
            decoded = decode_log(raw, address, pool.protocol)
            if decoded is not None:
                rows.append(decoded)

        if rows:
            frame = pd.DataFrame(rows)
            write_events(frame, pipeline.data_dir, address)
            total_events += len(rows)

        save_checkpoint(pipeline.checkpoint_dir, address, end)
        chunks += 1
        logger.info(
            "  chunk %d..%d: %d events (total=%d)", cursor, end, len(rows), total_events
        )
        cursor = end + 1

    return {
        "events": total_events,
        "from_block": from_block,
        "to_block": to_block,
        "chunks": chunks,
        "protocol": pool.protocol,
    }
