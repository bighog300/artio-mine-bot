"""Vercel serverless entry point.

Vercel routes all /api/* requests here via the rewrite in vercel.json.
Mangum adapts the ASGI app to the Lambda-compatible interface that Vercel
uses for Python serverless functions.
"""
import os

# Must be set before app modules are imported so Settings() picks them up.
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("PLAYWRIGHT_ENABLED", "false")

from mangum import Mangum  # noqa: E402

from app.api.main import app  # noqa: E402

# lifespan="off" skips startup/shutdown events (init_db) — use Alembic
# migrations to manage the schema in production.
handler = Mangum(app, lifespan="off")
