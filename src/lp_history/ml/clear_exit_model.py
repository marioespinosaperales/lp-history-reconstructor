"""Classifier: is this position's IL/HODL metric trustworthy (clear-exit)?"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from lp_history.ml.features import (
    FEATURE_COLUMNS,
    frame_from_mart_rows,
    synthesize_positions,
    xy_from_frame,
)
from lp_history.settings import PROJECT_ROOT


@dataclass(frozen=True)
class ClearExitModelResult:
    metrics: dict[str, Any]
    source: str


def _load_mart_frame(duckdb_path: Path) -> tuple[Any, str] | None:
    if not duckdb_path.exists():
        return None
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        tables = {r[0] for r in con.execute("show tables").fetchall()}
        if "mart_position_pnl" not in tables:
            return None
        df = con.execute("select * from mart_position_pnl").fetchdf()
        if df.empty or len(df) < 20:
            return None
        return frame_from_mart_rows(df.to_dict(orient="records")), str(duckdb_path)
    finally:
        con.close()


def train_clear_exit_model(
    frame=None,
    *,
    seed: int = 42,
    test_size: float = 0.25,
    source: str = "synthetic",
) -> ClearExitModelResult:
    if frame is None:
        frame = synthesize_positions(seed=seed)
        source = "synthetic"
    x, y = xy_from_frame(frame)
    if len(np.unique(y)) < 2:
        raise ValueError("Need both clear-exit and open positions to train")

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_size, random_state=seed, stratify=y
    )
    pipe = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    random_state=seed,
                    class_weight="balanced",
                ),
            ),
        ]
    )
    pipe.fit(x_train, y_train)
    pred = pipe.predict(x_test)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "f1_clear_exit": round(float(f1_score(y_test, pred, pos_label=1, zero_division=0.0)), 4),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "feature_columns": list(FEATURE_COLUMNS),
        "positive_rate": round(float(y.mean()), 4),
    }
    return ClearExitModelResult(metrics=metrics, source=source)


def train_from_warehouse_or_synthetic(
    duckdb_path: Path,
    *,
    seed: int = 42,
) -> ClearExitModelResult:
    loaded = _load_mart_frame(duckdb_path)
    if loaded is None:
        frame = synthesize_positions(seed=seed)
        return train_clear_exit_model(frame, seed=seed, source="synthetic")
    frame, source = loaded
    return train_clear_exit_model(frame, seed=seed, source=source)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# LP history clear-exit trust model report",
        "",
        "Logistic regression predicting whether a position is a clear-exit "
        "(IL vs HODL metrics are more trustworthy).",
        "",
        f"Generated: `{report.get('generated_at')}`",
        f"Source: `{report.get('source')}`",
        "",
        "## Holdout metrics",
        "",
        "```json",
        json.dumps(report.get("metrics", {}), indent=2),
        "```",
        "",
        "## Caveats",
        "",
    ]
    for c in report.get("caveats", []):
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict[str, Any], *, artifacts_dir: Path | None = None) -> Path:
    out_dir = artifacts_dir or (PROJECT_ROOT / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "ml_pnl_report.md"
    json_path = out_dir / "ml_pnl_report.json"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return md_path


def build_report(result: ClearExitModelResult) -> dict[str, Any]:
    caveats = [
        "Complements on-chain verify; does not replace ground-truth liquidity checks.",
        "Prefer clear-exit gated IL aggregates even when the model scores high.",
    ]
    if result.source == "synthetic":
        caveats.append(
            "Trained on synthetic positions (warehouse mart unavailable or too small)."
        )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": result.source,
        "metrics": result.metrics,
        "caveats": caveats,
    }
