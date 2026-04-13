FROM python:3.11-slim

WORKDIR /app

# System dependencies (curl for health checks; Playwright deps via install-deps)
RUN apt-get update && apt-get install -y curl libpq-dev && rm -rf /var/lib/apt/lists/*

# ── Dependency layer (cached until pyproject.toml changes) ────────────────────
COPY pyproject.toml .
# Install production deps only — no [dev] extras (pytest, ruff, etc.)
RUN pip install --no-cache-dir -e "."

# Install Playwright browsers to a fixed path inside /app
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright
RUN playwright install chromium && playwright install-deps chromium

# ── Application source ────────────────────────────────────────────────────────
# Copy only runtime files — tests, frontend, and docs are excluded via .dockerignore
COPY app/ ./app/
COPY alembic.ini .
COPY scripts/start.sh ./start.sh
RUN chmod +x ./start.sh

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN groupadd --system appuser \
    && useradd --system --gid appuser --uid 1001 appuser

# Ensure mounted volume path is writable for SQLite when running as non-root.
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

# data/ is created at runtime by ensure_data_dir() called from init_db()
EXPOSE 8000

# start.sh: runs alembic migrations then exec uvicorn (uvicorn becomes PID 1)
CMD ["./start.sh"]
