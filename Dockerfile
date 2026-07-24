# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data /app/warehouse /app/artifacts \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser config ./config
COPY --chown=appuser:appuser dbt ./dbt
COPY --chown=appuser:appuser tests ./tests

USER appuser

RUN uv sync --frozen

CMD ["sh", "-c", "uv run python -m lp_history.run && uv run python -m lp_history.build_warehouse && LP_DUCKDB_PATH=warehouse/lp.duckdb uv run dbt build --project-dir dbt --profiles-dir dbt"]
