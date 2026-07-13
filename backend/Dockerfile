FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY demo ./demo
COPY evaluation ./evaluation

RUN pip install --no-cache-dir . \
    && addgroup --system agentradar \
    && adduser --system --ingroup agentradar agentradar \
    && mkdir -p /app/data \
    && chown -R agentradar:agentradar /app

USER agentradar

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
