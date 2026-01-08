FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS builder

WORKDIR /app
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY src ./src
RUN uv sync --no-dev --compile-bytecode --extra api

FROM python:3.13-slim-bookworm AS runner

# Install git for GitPython dependency
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH="/app/src"
ENV ASSET_OUTPUT_DIR=/app/data/outputs
ENV PROJECT_ROOT=/app

COPY --from=builder /app/.venv /app/.venv
COPY data ./data

COPY src ./src
COPY entrypoint.sh /app/entrypoint.sh

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
