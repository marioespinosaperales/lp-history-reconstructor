"""Chunked NonfungiblePositionManager event backfill."""

from __future__ import annotations

import logging

import pandas as pd
from eth_utils import to_checksum_address

from lp_history.index.backfill import resolve_range
from lp_history.index.npm_abi import decode_log, topic0_set
from lp_history.load.checkpoint import save_checkpoint
from lp_history.load.parquet import write_events
from lp_history.rpc.client import RpcClient
from lp_history.settings import NpmConfig, PipelineConfig

logger = logging.getLogger(__name__)


def backfill_npm(
    rpc: RpcClient,
    npm: NpmConfig,
    pipeline: PipelineConfig,
) -> dict[str, int]:
    """Index NPM Transfer / IncreaseLiquidity / DecreaseLiquidity / Collect."""
    address = to_checksum_address(npm.address)
    from_block, to_block = resolve_range(rpc, pipeline, address, pipeline.checkpoint_dir)

    if from_block > to_block:
        logger.info("%s already caught up", npm.name)
        return {"events": 0, "from_block": from_block, "to_block": to_block, "chunks": 0}

    topics = {t.lower() for t in topic0_set()}
    total_events = 0
    chunks = 0
    cursor = from_block

    logger.info(
        "Backfilling NPM %s (%s) blocks %d..%d (chunk=%d)",
        npm.name,
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
            decoded = decode_log(raw, address)
            if decoded is not None:
                rows.append(decoded)

        if rows:
            write_events(pd.DataFrame(rows), pipeline.data_dir, address, kind="npm")
            total_events += len(rows)

        save_checkpoint(pipeline.checkpoint_dir, address, end)
        chunks += 1
        logger.info(
            "  npm chunk %d..%d: %d events (total=%d)", cursor, end, len(rows), total_events
        )
        cursor = end + 1

    return {
        "events": total_events,
        "from_block": from_block,
        "to_block": to_block,
        "chunks": chunks,
        "protocol": "uniswap_v3_npm",
    }
