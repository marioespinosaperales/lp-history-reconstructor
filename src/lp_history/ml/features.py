"""Position features for clear-exit trust modeling."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "range_width_ticks",
    "range_width_pct",
    "bucket_narrow",
    "bucket_mid",
    "bucket_wide",
    "bucket_full",
    "deposited_token0",
    "fees_proxy_token0",
    "fees_on_deposit_pct",
    "withdrawn_frac",
]


def _bucket_flags(bucket: str) -> dict[str, int]:
    return {
        "bucket_narrow": int(bucket == "narrow"),
        "bucket_mid": int(bucket == "mid"),
        "bucket_wide": int(bucket == "wide"),
        "bucket_full": int(bucket == "full"),
    }


def synthesize_positions(*, n: int = 120, seed: int = 42) -> pd.DataFrame:
    """Labeled synthetic positions when the warehouse mart is unavailable."""
    rng = np.random.default_rng(seed)
    buckets = ["narrow", "mid", "wide", "full"]
    rows: list[dict[str, Any]] = []
    for i in range(n):
        bucket = str(rng.choice(buckets, p=[0.35, 0.3, 0.25, 0.1]))
        width = {
            "narrow": float(rng.uniform(10, 200)),
            "mid": float(rng.uniform(200, 800)),
            "wide": float(rng.uniform(800, 3000)),
            "full": float(rng.uniform(3000, 20000)),
        }[bucket]
        deposited = float(rng.uniform(0.5, 50.0))
        # Clear exits tend to withdraw most liquidity
        # Primary signal: withdrawn fraction; small label noise keeps the task non-trivial.
        withdrawn_frac = float(rng.uniform(0.0, 1.0))
        is_clear = withdrawn_frac >= 0.85
        if rng.random() < 0.02:
            is_clear = not is_clear
        fees = deposited * float(rng.uniform(0.0, 0.08))
        fees_pct = (fees / deposited) * 100.0
        rows.append(
            {
                "position_id": i,
                "range_width_ticks": width,
                "range_width_pct": width / 100.0,
                "range_bucket": bucket,
                "deposited_token0": deposited,
                "fees_proxy_token0": fees,
                "fees_on_deposit_pct": fees_pct,
                "withdrawn_frac": withdrawn_frac,
                "is_clear_exit": is_clear,
                **_bucket_flags(bucket),
            }
        )
    return pd.DataFrame.from_records(rows)


def frame_from_mart_rows(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for i, r in enumerate(records):
        bucket = str(r.get("range_bucket") or "mid")
        deposited = float(r.get("deposited_token0") or 0.0)
        collected = float(r.get("collected_token0") or 0.0)
        decreased = float(r.get("decreased_token0") or r.get("withdrawn_token0") or 0.0)
        withdrawn_frac = min(1.0, (decreased / deposited)) if deposited > 0 else 0.0
        is_clear = (
            bool(r["is_clear_exit"]) if "is_clear_exit" in r else withdrawn_frac >= 0.85
        )
        rows.append(
            {
                "position_id": i,
                "range_width_ticks": float(r.get("range_width_ticks") or 0.0),
                "range_width_pct": float(r.get("range_width_pct") or 0.0),
                "range_bucket": bucket,
                "deposited_token0": deposited,
                "fees_proxy_token0": float(
                    r.get("fees_proxy_token0") or max(collected - decreased, 0.0)
                ),
                "fees_on_deposit_pct": float(r.get("fees_on_deposit_pct") or 0.0),
                "withdrawn_frac": withdrawn_frac,
                "is_clear_exit": is_clear,
                **_bucket_flags(bucket),
            }
        )
    return pd.DataFrame.from_records(rows)


def xy_from_frame(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    x = frame[FEATURE_COLUMNS].to_numpy(dtype=float)
    y = frame["is_clear_exit"].astype(int).to_numpy()
    return x, y
