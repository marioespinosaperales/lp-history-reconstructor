"""CLI: ``uv run python -m lp_history.ml`` → artifacts/ml_pnl_report.md"""

from __future__ import annotations

import argparse
import logging
import sys

from lp_history.ml.clear_exit_model import (
    build_report,
    train_from_warehouse_or_synthetic,
    write_report,
)
from lp_history.settings import get_settings

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="LP clear-exit trust model report")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    settings = get_settings()
    result = train_from_warehouse_or_synthetic(settings.pipeline.duckdb_path, seed=args.seed)
    report = build_report(result)
    path = write_report(report)
    logger.info(
        "Wrote ML report → %s (f1_clear_exit=%.3f source=%s)",
        path,
        result.metrics.get("f1_clear_exit", 0.0),
        result.source,
    )
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
