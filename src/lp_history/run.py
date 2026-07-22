"""CLI entrypoint: backfill -> fold Sync -> verify getReserves().

    uv run python -m lp_history.run
"""

from __future__ import annotations

import logging
import sys

from lp_history.index.backfill import backfill_pool
from lp_history.rpc.client import RpcClient
from lp_history.settings import get_settings, require_rpc_url
from lp_history.verify.check import verify_pool

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

    failed = False
    for pool in settings.pools:
        stats = backfill_pool(rpc, pool, pipeline)
        logger.info("Backfill %s: %s", pool.name, stats)
        result = verify_pool(rpc, pipeline.data_dir, pool.address)
        logger.info("Verify %s: %s", pool.name, result.message)
        if not result.ok:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
