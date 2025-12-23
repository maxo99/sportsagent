FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS builder

WORKDIR /app
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY src ./src
RUN uv sync --no-dev --compile-bytecode --locked

FROM python:3.13-slim-bookworm AS runner

WORKDIR /app
ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH="/app/src"
ENV ASSET_OUTPUT_DIR=/app/data/outputs

COPY --from=builder /app/.venv /app/.venv
COPY data ./data

COPY src ./src

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/.venv/bin/uvicorn"]
CMD ["sportsagent.api:app", "--host", "0.0.0.0", "--port", "8000"]
