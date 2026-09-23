# syntax=docker/dockerfile:1.7
# Stage 1: resolve and install dependencies with uv (heavy image, cached layers).
FROM ghcr.io/astral-sh/uv:0.9.30-python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Manifests first: this layer is cached until dependencies change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
# Code last: changes often, invalidates only the layers below.
COPY . .

# Stage 2: minimal runtime, no uv, no build tools, non-root.
FROM python:3.12.11-slim-bookworm
RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
# Uses python instead of curl so the runtime image stays without extra packages.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"]
# Exec form: uvicorn becomes PID 1 and receives SIGTERM directly for graceful shutdown.
CMD ["python", "-m", "src"]
