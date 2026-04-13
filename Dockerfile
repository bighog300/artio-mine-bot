FROM python:3.11-slim

WORKDIR /app

# System dependencies (curl for health checks; libpq for asyncpg build/runtime)
RUN apt-get update && apt-get install -y --no-install-recommends curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Dependency layer (cached until pyproject.toml changes) ────────────────────
COPY pyproject.toml .
# Install production deps only — no [dev] extras (pytest, ruff, etc.)
RUN pip install --no-cache-dir -e "." \
    && pip install --no-cache-dir asyncpg

# Install Playwright browsers to a fixed path inside /app
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright
RUN playwright install chromium && playwright install-deps chromium

# ── Application source ────────────────────────────────────────────────────────
COPY app/ ./app/
COPY api/ ./api/
COPY alembic.ini .
COPY scripts/start.sh ./start.sh
RUN chmod +x ./start.sh

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN groupadd --system appuser \
    && useradd --system --gid appuser --uid 1001 appuser

RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["./start.sh"]
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
