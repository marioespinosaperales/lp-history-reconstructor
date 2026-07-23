"""CLI entrypoint: pool backfill + NPM wallet attribution + on-chain verify.

    uv run python -m lp_history.run
"""

from __future__ import annotations

import logging
import sys

from lp_history.index.backfill import backfill_pool
from lp_history.index.npm_backfill import backfill_npm
from lp_history.rpc.client import RpcClient
from lp_history.settings import get_settings, require_rpc_url
from lp_history.verify.check import verify_pool
from lp_history.verify.npm_check import verify_npm_for_pool
from lp_history.verify.v3_check import verify_v3_pool

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
    pools = [p for p in settings.pools if p.enabled]
    if not pools and not settings.npm.enabled:
        logger.error("No enabled pools or NPM in config/")
        return 1

    for pool in pools:
        stats = backfill_pool(rpc, pool, pipeline)
        logger.info("Backfill %s: %s", pool.name, stats)

        if pool.protocol == "uniswap_v3":
            result = verify_v3_pool(rpc, pipeline.data_dir, pool.address)
            for pos in result.sample_positions:
                logger.info(
                    "  pool position owner=%s range=[%d,%d) width=%d L=%d",
                    pos.owner,
                    pos.tick_lower,
                    pos.tick_upper,
                    pos.range_width_ticks,
                    pos.liquidity,
                )
        elif pool.protocol == "uniswap_v2":
            result = verify_pool(rpc, pipeline.data_dir, pool.address)
        else:
            logger.error("Unsupported protocol %s", pool.protocol)
            failed = True
            continue

        logger.info("Verify %s: %s", pool.name, result.message)
        if not result.ok:
            failed = True

    if settings.npm.enabled:
        npm_stats = backfill_npm(rpc, settings.npm, pipeline)
        logger.info("Backfill NPM: %s", npm_stats)

        v3_pools = [p for p in pools if p.protocol == "uniswap_v3"]
        for pool in v3_pools:
            npm_result = verify_npm_for_pool(
                rpc,
                pipeline.data_dir,
                settings.npm.address,
                pool,
                sample_size=pipeline.npm_verify_sample,
            )
            logger.info("Verify NPM↔%s: %s", pool.name, npm_result.message)
            for pos in npm_result.samples:
                logger.info(
                    "  wallet=%s tokenId=%s range=[%s,%s) width=%s on_chain_L=%s",
                    pos.wallet,
                    pos.token_id,
                    pos.tick_lower,
                    pos.tick_upper,
                    pos.range_width_ticks,
                    pos.liquidity,
                )
            if not npm_result.ok:
                failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
