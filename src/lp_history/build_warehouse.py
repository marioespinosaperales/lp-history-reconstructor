"""Build DuckDB warehouse: NFT snapshot → load Parquet → ready for dbt.

    uv run python -m lp_history.build_warehouse
"""

from __future__ import annotations

import logging
import sys

from lp_history.analytics.positions_snapshot import write_nft_positions_snapshot
from lp_history.load.duckdb_loader import load_raw_tables
from lp_history.rpc.client import RpcClient
from lp_history.settings import get_settings, require_rpc_url

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    url = require_rpc_url(settings)
    pipeline = settings.pipeline
    rpc = RpcClient(
        url,
        timeout_seconds=pipeline.rpc_timeout_seconds,
        max_retries=pipeline.rpc_max_retries,
        backoff_seconds=pipeline.rpc_backoff_seconds,
    )

    if settings.npm.enabled:
        for pool in settings.pools:
            if not pool.enabled or pool.protocol != "uniswap_v3":
                continue
            write_nft_positions_snapshot(
                rpc,
                pipeline.data_dir,
                settings.npm.address,
                pool,
                max_calls=pipeline.npm_snapshot_max_calls,
                max_matches=pipeline.npm_snapshot_max_matches,
            )

    counts = load_raw_tables(pipeline.duckdb_path, pipeline.data_dir)
    logger.info("Warehouse ready at %s: %s", pipeline.duckdb_path, counts)
    return 0 if counts else 1


if __name__ == "__main__":
    sys.exit(main())
