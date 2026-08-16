FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "minervini_scanner.api:app", "--host", "0.0.0.0", "--port", "8000"]
