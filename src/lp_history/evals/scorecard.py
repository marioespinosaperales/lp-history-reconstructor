"""QC scorecard: on-chain verify outcomes + mart usefulness sanity checks.

Answers: is reconstructed LP state trustworthy enough for fees/IL analysis,
and are the mart metrics directionally usable given lookback limits?
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from lp_history.settings import PROJECT_ROOT


@dataclass(frozen=True)
class VerifyCheck:
    name: str
    status: str  # exact | partial_or_smoke | fail | skipped
    ok: bool
    message: str


@dataclass
class Scorecard:
    generated_at: str
    verify_checks: list[VerifyCheck] = field(default_factory=list)
    verify_summary: dict[str, int] = field(default_factory=dict)
    mart: dict[str, Any] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "verify_checks": [asdict(c) for c in self.verify_checks],
            "verify_summary": self.verify_summary,
            "mart": self.mart,
            "caveats": self.caveats,
        }


def classify_verify_status(message: str, ok: bool) -> str:
    """Map verify message text to a coarse eval label."""
    if message.startswith("PASS"):
        return "exact"
    if "SMOKE_OK" in message or message.startswith("PARTIAL") or "PARTIAL at" in message:
        return "partial_or_smoke"
    if not ok:
        return "fail"
    return "exact" if ok else "fail"


def summarize_verify_results(checks: list[VerifyCheck]) -> dict[str, int]:
    summary = {"exact": 0, "partial_or_smoke": 0, "fail": 0, "skipped": 0, "total": len(checks)}
    for check in checks:
        summary[check.status] = summary.get(check.status, 0) + 1
    return summary


def mart_sanity(duckdb_path: Path) -> dict[str, Any]:
    """Sanity metrics over PnL marts when the warehouse exists."""
    if not duckdb_path.exists():
        return {"available": False, "reason": f"warehouse not found: {duckdb_path}"}

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        tables = {r[0] for r in con.execute("show tables").fetchall()}
        if "mart_position_pnl" not in tables:
            return {"available": False, "reason": "mart_position_pnl missing"}

        row = con.execute(
            """
            select
                count(*) as positions,
                count(*) filter (where is_clear_exit) as clear_exits,
                count(distinct range_bucket) as range_buckets,
                count(*) filter (where il_vs_hodl_pct is not null) as with_il
            from mart_position_pnl
            """
        ).fetchone()
        assert row is not None
        positions, clear_exits, range_buckets, with_il = row
        clear_exit_rate = (clear_exits / positions) if positions else 0.0

        bucket_rows = []
        if "mart_pnl_by_range_width" in tables:
            bucket_rows = con.execute(
                """
                select range_bucket, positions, clear_exits
                from mart_pnl_by_range_width
                order by range_bucket
                """
            ).fetchall()

        return {
            "available": True,
            "positions": int(positions),
            "clear_exits": int(clear_exits),
            "clear_exit_rate": round(clear_exit_rate, 4),
            "range_buckets": int(range_buckets),
            "positions_with_il": int(with_il),
            "by_range_bucket": [
                {"range_bucket": b[0], "positions": int(b[1]), "clear_exits": int(b[2])}
                for b in bucket_rows
            ],
        }
    finally:
        con.close()


def build_scorecard(
    checks: list[VerifyCheck],
    *,
    duckdb_path: Path | None = None,
    lookback_blocks: int | None = None,
) -> Scorecard:
    mart = mart_sanity(duckdb_path) if duckdb_path is not None else {"available": False}
    caveats: list[str] = []
    if lookback_blocks is not None and lookback_blocks < 50_000:
        caveats.append(
            f"lookback_blocks={lookback_blocks} is short; V3 liquidity verify may be "
            "PARTIAL/SMOKE_OK and fees/IL marts are directional, not full-history truth."
        )
    if mart.get("available") and mart.get("clear_exit_rate", 1.0) < 0.2:
        caveats.append(
            "Low clear-exit coverage: IL vs HODL can look falsely extreme on open positions; "
            "prefer clear-exit gated aggregates."
        )
    if any(c.status == "partial_or_smoke" for c in checks):
        caveats.append(
            "At least one verify check is partial/smoke — reconstruction is usable for "
            "pipeline smoke tests but not bit-identical to full on-chain history."
        )

    return Scorecard(
        generated_at=datetime.now(UTC).isoformat(),
        verify_checks=checks,
        verify_summary=summarize_verify_results(checks),
        mart=mart,
        caveats=caveats,
    )


def render_markdown(scorecard: Scorecard) -> str:
    lines = [
        "# LP history QC scorecard",
        "",
        f"Generated: `{scorecard.generated_at}`",
        "",
        "## On-chain verify",
        "",
        "| Check | Status | OK | Message |",
        "|---|---|---|---|",
    ]
    for c in scorecard.verify_checks:
        msg = c.message.replace("|", "\\|")
        lines.append(f"| {c.name} | {c.status} | {c.ok} | {msg} |")
    lines.extend(
        [
            "",
            "### Summary",
            "",
            "```json",
            json.dumps(scorecard.verify_summary, indent=2),
            "```",
            "",
            "## Mart sanity",
            "",
            "```json",
            json.dumps(scorecard.mart, indent=2),
            "```",
            "",
            "## Caveats",
            "",
        ]
    )
    if scorecard.caveats:
        lines.extend(f"- {c}" for c in scorecard.caveats)
    else:
        lines.append("- None recorded.")
    lines.append("")
    return "\n".join(lines)


def write_scorecard(
    scorecard: Scorecard,
    *,
    artifacts_dir: Path | None = None,
) -> Path:
    out_dir = artifacts_dir or (PROJECT_ROOT / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "qc_scorecard.md"
    json_path = out_dir / "qc_scorecard.json"
    md_path.write_text(render_markdown(scorecard), encoding="utf-8")
    json_path.write_text(json.dumps(scorecard.to_dict(), indent=2) + "\n", encoding="utf-8")
    return md_path


def collect_live_verify_checks() -> tuple[list[VerifyCheck], int | None]:
    """Run live verify against configured pools (requires RPC)."""
    from lp_history.rpc.client import RpcClient
    from lp_history.settings import get_settings, require_rpc_url
    from lp_history.verify.check import verify_pool
    from lp_history.verify.npm_check import verify_npm_for_pool
    from lp_history.verify.v3_check import verify_v3_pool

    settings = get_settings()
    url = require_rpc_url(settings)
    pipeline = settings.pipeline
    rpc = RpcClient(
        url,
        timeout_seconds=pipeline.rpc_timeout_seconds,
        max_retries=pipeline.rpc_max_retries,
        backoff_seconds=pipeline.rpc_backoff_seconds,
    )

    checks: list[VerifyCheck] = []
    pools = [p for p in settings.pools if p.enabled]
    for pool in pools:
        if pool.protocol == "uniswap_v3":
            result = verify_v3_pool(rpc, pipeline.data_dir, pool.address)
        elif pool.protocol == "uniswap_v2":
            result = verify_pool(rpc, pipeline.data_dir, pool.address)
        else:
            checks.append(
                VerifyCheck(
                    name=pool.name,
                    status="skipped",
                    ok=False,
                    message=f"Unsupported protocol {pool.protocol}",
                )
            )
            continue
        status = classify_verify_status(result.message, result.ok)
        checks.append(
            VerifyCheck(name=pool.name, status=status, ok=result.ok, message=result.message)
        )

    if settings.npm.enabled:
        for pool in pools:
            if pool.protocol != "uniswap_v3":
                continue
            npm_result = verify_npm_for_pool(
                rpc,
                pipeline.data_dir,
                settings.npm.address,
                pool,
                sample_size=pipeline.npm_verify_sample,
            )
            status = classify_verify_status(npm_result.message, npm_result.ok)
            checks.append(
                VerifyCheck(
                    name=f"npm::{pool.name}",
                    status=status,
                    ok=npm_result.ok,
                    message=npm_result.message,
                )
            )

    return checks, pipeline.lookback_blocks
