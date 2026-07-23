"""Load Parquet event store + NFT snapshots into DuckDB for dbt."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


def _replace_from_glob(conn: duckdb.DuckDBPyConnection, table: str, glob: str) -> int:
    conn.execute(
        f"""
        CREATE OR REPLACE TABLE {table} AS
        SELECT * FROM read_parquet('{glob}', hive_partitioning = true, union_by_name = true)
        """
    )
    return int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])


def load_raw_tables(duckdb_path: Path, data_dir: Path, raw_schema: str = "raw") -> dict[str, int]:
    """(Re)create raw tables from Hive Parquet under ``data_dir``."""
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    data = data_dir.as_posix()

    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_schema}")

        pool_glob = f"{data}/events/pool=*/ingested_date=*/*.parquet"
        if list(data_dir.glob("events/pool=*/ingested_date=*/*.parquet")):
            counts["pool_events"] = _replace_from_glob(
                conn, f"{raw_schema}.pool_events", pool_glob
            )
            logger.info("%s.pool_events: %d rows", raw_schema, counts["pool_events"])
        else:
            logger.warning("No pool event parquet under %s", data_dir)

        npm_glob = f"{data}/npm/address=*/ingested_date=*/*.parquet"
        if list(data_dir.glob("npm/address=*/ingested_date=*/*.parquet")):
            counts["npm_events"] = _replace_from_glob(conn, f"{raw_schema}.npm_events", npm_glob)
            logger.info("%s.npm_events: %d rows", raw_schema, counts["npm_events"])
        else:
            logger.warning("No NPM event parquet under %s", data_dir)

        nft_glob = f"{data}/analytics/nft_positions/pool=*/*.parquet"
        if list(data_dir.glob("analytics/nft_positions/pool=*/*.parquet")):
            counts["nft_positions"] = _replace_from_glob(
                conn, f"{raw_schema}.nft_positions", nft_glob
            )
            logger.info("%s.nft_positions: %d rows", raw_schema, counts["nft_positions"])
        else:
            logger.warning("No NFT position snapshots under %s", data_dir)

    return counts
