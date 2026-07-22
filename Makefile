# Requires make (on Windows: Git Bash, or `winget install GnuWin32.Make`).

.PHONY: install lint test backfill verify pipeline

install:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

backfill:
	uv run python -m lp_history.run

pipeline: backfill
