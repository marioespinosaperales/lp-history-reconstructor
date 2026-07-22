"""Chunked Uniswap V2 event backfill via eth_getLogs."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from eth_utils import to_checksum_address

from lp_history.index.abi import decode_log, topic0_set
from lp_history.load.checkpoint import load_checkpoint, save_checkpoint
from lp_history.load.parquet import write_events
from lp_history.rpc.client import RpcClient
from lp_history.settings import PipelineConfig, PoolConfig

logger = logging.getLogger(__name__)


def resolve_range(
    rpc: RpcClient,
    pipeline: PipelineConfig,
    pool: PoolConfig,
    checkpoint_dir: Path,
) -> tuple[int, int]:
    """Return (from_block, to_block_inclusive) for this run."""
    tip = rpc.block_number()
    to_block = tip - pipeline.confirmations
    if to_block < 0:
        raise RuntimeError("Chain tip is below confirmation depth")

    checkpoint = load_checkpoint(checkpoint_dir, pool.address)
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
    from_block, to_block = resolve_range(rpc, pipeline, pool, pipeline.checkpoint_dir)

    if from_block > to_block:
        logger.info(
            "%s already caught up (checkpoint >= tip-%d)", pool.name, pipeline.confirmations
        )
        return {"events": 0, "from_block": from_block, "to_block": to_block, "chunks": 0}

    topics = topic0_set()
    # Filter by any of the four event topic0s: OR by listing them in position 0
    # is not valid JSON-RPC; we omit topics and filter after decode, OR pass
    # each topic in separate calls. One call without topic filter is simpler
    # and fine for a single pool address.
    total_events = 0
    chunks = 0
    cursor = from_block

    logger.info(
        "Backfilling %s (%s) blocks %d..%d (chunk=%d)",
        pool.name,
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
            # Only keep known V2 events (topic0 filter)
            topic0 = (raw.get("topics") or [None])[0]
            if topic0 is None or topic0.lower() not in {t.lower() for t in topics}:
                continue
            decoded = decode_log(raw, address)
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
    }
