# base — shared foundation
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src
RUN groupadd -r ploutos && useradd -r -g ploutos -d /app ploutos
WORKDIR /app

# deps-dev — all deps including alembic
FROM base AS deps-dev
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# deps-prod — runtime deps only
FROM base AS deps-prod
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# migrate — runs alembic upgrade head
FROM deps-dev AS migrate
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY src/ ./src/
USER ploutos
CMD [".venv/bin/alembic", "upgrade", "head"]

# runtime — production server
FROM deps-prod AS runtime
COPY src/ ./src/
USER ploutos
ENV APP_HOST=0.0.0.0 APP_PORT=8000
EXPOSE ${APP_PORT}
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen(f'http://localhost:${APP_PORT}/health')"
CMD .venv/bin/uvicorn ploutos.main:app --host ${APP_HOST} --port ${APP_PORT}
