# Requires make (on Windows: Git Bash, or `winget install GnuWin32.Make`).

.PHONY: install lint test backfill warehouse transform snapshot pipeline

install:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

backfill:
	uv run python -m lp_history.run

warehouse:
	uv run python -m lp_history.build_warehouse

transform: warehouse
	LP_DUCKDB_PATH=warehouse/lp.duckdb uv run dbt build --project-dir dbt --profiles-dir dbt

snapshot:
	uv run python -m lp_history.export_snapshot

pipeline: backfill transform snapshot
