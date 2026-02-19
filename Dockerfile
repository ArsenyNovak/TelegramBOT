FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

WORKDIR /app
COPY pyproject.toml uv.lock .
RUN uv sync --frozen --no-dev

COPY . /app

EXPOSE 8000

# CMD uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
CMD uv run python -m app.main



